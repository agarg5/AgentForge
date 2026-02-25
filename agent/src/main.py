import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from langgraph.errors import GraphRecursionError

from .agent import MAX_AGENT_STEPS, create_agent
from .client import GhostfolioClient
from .memory import ChatHistoryStore, MemoryStore
from .observability import calculate_cost, configure_tracing, extract_metrics, get_run_config
from .verification import verify_response

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentforge")

# Sliding window: max messages sent to the LLM to manage context size and cost.
# 50 messages ≈ 25 conversation turns (user + agent).
MAX_HISTORY_MESSAGES = 50


def trim_messages(messages: list, max_messages: int = MAX_HISTORY_MESSAGES) -> list:
    """Trim a message list to the most recent *max_messages* entries."""
    if len(messages) > max_messages:
        return messages[-max_messages:]
    return messages

app = FastAPI(title="AgentForge", version="0.1.0")

GHOSTFOLIO_BASE_URL = os.getenv("GHOSTFOLIO_BASE_URL", "http://localhost:3333")
REDIS_URL = os.getenv("REDIS_URL")

# Create agent once at startup (stateless — per-request state via config)
agent = create_agent()

# Initialize persistent memory store
_redis_client = None
if REDIS_URL:
    try:
        import redis.asyncio as aioredis

        _redis_client = aioredis.from_url(REDIS_URL, decode_responses=False)
        logger.info("Redis memory store: connected (%s)", REDIS_URL.split("@")[-1] if "@" in REDIS_URL else "local")
    except ImportError:
        logger.warning("redis package not installed — using in-memory fallback")
    except Exception as e:
        logger.warning("Redis connection failed — using in-memory fallback: %s", e)
else:
    logger.info("REDIS_URL not set — using in-memory memory store")

memory_store = MemoryStore(redis_client=_redis_client)
chat_history_store = ChatHistoryStore(redis_client=_redis_client)

# Check LangSmith tracing on startup
tracing_active = configure_tracing()
logger.info("LangSmith tracing: %s", "enabled" if tracing_active else "disabled")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    role: str = "agent"
    content: str
    tools_used: list[str] = []
    tool_count: int = 0
    run_id: Optional[str] = None
    metrics: Optional[dict] = None


class FeedbackRequest(BaseModel):
    run_id: str
    score: float  # 1.0 = positive, 0.0 = negative
    comment: Optional[str] = None


def _extract_token(authorization: str) -> str:
    """Extract and validate the auth token from the Authorization header."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    return token


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tracing": tracing_active,
        "memory": "redis" if memory_store.is_persistent else "in-memory",
        "chat_history": "redis" if chat_history_store.is_persistent else "in-memory",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, authorization: str = Header()):
    token = _extract_token(authorization)

    # Load persisted history if the frontend didn't send any
    messages = []
    if body.history:
        for msg in body.history:
            if msg.role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif msg.role in ("agent", "assistant"):
                messages.append(AIMessage(content=msg.content))
    else:
        stored_history = await chat_history_store.get_history(token)
        for msg in stored_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] in ("agent", "assistant"):
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=body.message))

    # Sliding window: keep only recent messages to manage context size
    total_before = len(messages)
    messages = trim_messages(messages)
    if len(messages) < total_before:
        logger.info(
            "Context window trimmed from %d to %d messages",
            total_before,
            len(messages),
        )

    # Build LangSmith run config with tracing metadata
    run_config = get_run_config(
        session_id=body.session_id,
        tags=["chat"],
        metadata={
            "message_length": len(body.message),
            "message_count": len(messages),
            "messages_trimmed": total_before - len(messages),
        },
    )
    run_config["configurable"] = {
        "memory": memory_store,
        "auth_token": token,
    }
    # Prevent runaway tool-call loops by capping the number of LangGraph steps
    run_config["recursion_limit"] = MAX_AGENT_STEPS

    start_time = time.monotonic()
    run_id = run_config.get("run_id")

    try:
        async with GhostfolioClient(base_url=GHOSTFOLIO_BASE_URL, auth_token=token) as client:
            run_config["configurable"]["client"] = client
            result = await agent.ainvoke(
                {"messages": messages},
                config=run_config,
            )
    except GraphRecursionError:
        elapsed = time.monotonic() - start_time
        logger.error("Agent hit recursion limit run_id=%s latency=%.2fs", run_id, elapsed)
        return ChatResponse(
            content="I ran into a complexity limit while processing your request. Could you try rephrasing with a more specific question?",
            run_id=run_id,
            metrics={"error": "recursion_limit_reached", "latency_seconds": round(elapsed, 3)},
        )
    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error("Agent error run_id=%s latency=%.2fs: %s", run_id, elapsed, e)
        return ChatResponse(
            content="I'm sorry, I encountered an error processing your request. Please try again.",
            run_id=run_id,
            metrics={"error": str(e), "latency_seconds": round(elapsed, 3)},
        )

    elapsed = time.monotonic() - start_time

    # Extract token usage and tool call metrics
    metrics = extract_metrics(result)
    metrics["latency_seconds"] = round(elapsed, 3)
    metrics["cost"] = calculate_cost(
        input_tokens=metrics["input_tokens"],
        output_tokens=metrics["output_tokens"],
    )

    logger.info(
        "chat run_id=%s latency=%.2fs tokens=%d tools=%d",
        run_id,
        elapsed,
        metrics["total_tokens"],
        metrics["tool_call_count"],
    )

    # Extract the final assistant message and tool outputs
    result_messages = result.get("messages", [])
    tool_outputs = [
        msg.content
        for msg in result_messages
        if msg.type == "tool" and isinstance(msg.content, str)
    ]

    for msg in reversed(result_messages):
        if hasattr(msg, "content") and msg.type == "ai" and msg.content:
            # Run verification layer (safe — won't crash the response)
            verification = verify_response(
                response=msg.content,
                tools_used=metrics.get("tools_used", []),
                tool_outputs=tool_outputs,
            )
            metrics["verification"] = verification["checks"]

            response_content = verification["response"]

            # Deduplicate tools_used while preserving first-seen order
            seen = set()
            unique_tools = []
            for t in metrics.get("tools_used", []):
                if t not in seen:
                    seen.add(t)
                    unique_tools.append(t)

            # Persist both messages to chat history
            await chat_history_store.append_message(token, "user", body.message)
            await chat_history_store.append_message(token, "agent", response_content)

            return ChatResponse(
                content=response_content,
                tools_used=unique_tools,
                tool_count=len(unique_tools),
                run_id=run_id,
                metrics=metrics,
            )

    return ChatResponse(
        content="I wasn't able to generate a response. Please try again.",
        run_id=run_id,
        metrics=metrics,
    )


@app.get("/chat/history")
async def get_chat_history(authorization: str = Header()):
    """Return the stored chat history for the current user."""
    token = _extract_token(authorization)
    history = await chat_history_store.get_history(token)
    return {"history": history}


@app.delete("/chat/history")
async def clear_chat_history(authorization: str = Header()):
    """Clear the stored chat history for the current user."""
    token = _extract_token(authorization)
    await chat_history_store.clear_history(token)
    return {"status": "ok"}


@app.post("/feedback")
async def feedback(body: FeedbackRequest):
    """Submit user feedback (thumbs up/down) for a chat response.

    Links feedback to the LangSmith trace via run_id so you can
    filter by user satisfaction in the dashboard.
    """
    try:
        from langsmith import Client

        ls_client = Client()
        ls_client.create_feedback(
            run_id=body.run_id,
            key="user-score",
            score=body.score,
            comment=body.comment,
        )
        return {"status": "ok", "run_id": body.run_id}
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="langsmith package not installed",
        )
    except Exception as e:
        logger.error("Failed to submit feedback: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
