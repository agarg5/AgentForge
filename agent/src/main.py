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
from .observability import configure_tracing, extract_metrics, get_run_config

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agentforge")

app = FastAPI(title="AgentForge", version="0.1.0")

GHOSTFOLIO_BASE_URL = os.getenv("GHOSTFOLIO_BASE_URL", "http://localhost:3333")

# Create agent once at startup (stateless — per-request state via config)
agent = create_agent()

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
    return {"status": "ok", "tracing": tracing_active}


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
    run_config["configurable"] = {}

    start_time = time.monotonic()

    async with GhostfolioClient(base_url=GHOSTFOLIO_BASE_URL, auth_token=token) as client:
        run_config["configurable"]["client"] = client
        result = await agent.ainvoke(
            {"messages": messages},
            config=run_config,
        )

    elapsed = time.monotonic() - start_time

    # Extract token usage and tool call metrics
    metrics = extract_metrics(result)
    metrics["latency_seconds"] = round(elapsed, 3)
    run_id = run_config.get("run_id")

    logger.info(
        "chat run_id=%s latency=%.2fs tokens=%d tools=%d",
        run_id,
        elapsed,
        metrics["total_tokens"],
        metrics["tool_call_count"],
    )

    # Extract the final assistant message
    result_messages = result.get("messages", [])
    for msg in reversed(result_messages):
        if hasattr(msg, "content") and msg.type == "ai" and msg.content:
            return ChatResponse(
                content=msg.content,
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
