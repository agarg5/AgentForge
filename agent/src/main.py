import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from .agent import create_agent
from .client import GhostfolioClient

load_dotenv()

app = FastAPI(title="AgentForge", version="0.1.0")

GHOSTFOLIO_BASE_URL = os.getenv("GHOSTFOLIO_BASE_URL", "http://localhost:3333")

# Create agent once at startup (stateless — per-request state via config)
agent = create_agent()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[list[ChatMessage]] = None


class ChatResponse(BaseModel):
    role: str = "agent"
    content: str


@app.get("/health")
async def health():
    return {"status": "ok"}


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

    async with GhostfolioClient(base_url=GHOSTFOLIO_BASE_URL, auth_token=token) as client:
        result = await agent.ainvoke(
            {"messages": messages},
            config={"configurable": {"client": client}},
        )

    # Extract the final assistant message
    result_messages = result.get("messages", [])
    for msg in reversed(result_messages):
        if hasattr(msg, "content") and msg.type == "ai" and msg.content:
            return ChatResponse(content=msg.content)

    return ChatResponse(content="I wasn't able to generate a response. Please try again.")
