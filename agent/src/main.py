import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from .agent import create_agent
from .client import GhostfolioClient
from .memory import MemoryStore
from .observability import calculate_cost, configure_tracing, extract_metrics, get_run_config
from .verification import verify_response

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentforge")

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
    run_id: Optional[str] = None
    metrics: Optional[dict] = None


class FeedbackRequest(BaseModel):
    run_id: str
    score: float  # 1.0 = positive, 0.0 = negative
    comment: Optional[str] = None


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "tracing": tracing_active,
        "memory": "redis" if memory_store.is_persistent else "in-memory",
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, authorization: str = Header()):
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")

    # Build message history for multi-turn conversation
    messages = []
    for msg in body.history or []:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role in ("agent", "assistant"):
            messages.append(AIMessage(content=msg.content))
    messages.append(HumanMessage(content=body.message))

    # Build LangSmith run config with tracing metadata
    run_config = get_run_config(
        session_id=body.session_id,
        tags=["chat"],
        metadata={"message_length": len(body.message)},
    )
    run_config["configurable"] = {
        "memory": memory_store,
        "auth_token": token,
    }

    start_time = time.monotonic()
    run_id = run_config.get("run_id")

    try:
        async with GhostfolioClient(base_url=GHOSTFOLIO_BASE_URL, auth_token=token) as client:
            run_config["configurable"]["client"] = client
            result = await agent.ainvoke(
                {"messages": messages},
                config=run_config,
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

            return ChatResponse(
                content=verification["response"],
                run_id=run_id,
                metrics=metrics,
            )

    return ChatResponse(
        content="I wasn't able to generate a response. Please try again.",
        run_id=run_id,
        metrics=metrics,
    )


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
