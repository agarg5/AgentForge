# AgentForge — AI Agent

A LangChain-based AI agent that wraps the Ghostfolio REST API, providing natural language portfolio analysis, market data queries, and financial guidance.

## Architecture

```
FastAPI (/chat endpoint)
  → Build message history (from request or Redis)
  → Sliding window trim
  → LangChain agent (GPT-4o) with 9 tools
  → Verification layer
  → Persist to Redis chat history
  → Return response + metrics
```

### Tools

| # | Tool | Description |
|---|------|-------------|
| 1 | `portfolio_analysis` | Holdings, allocation, performance |
| 2 | `transaction_history` | Activity list with filters |
| 3 | `market_data` | Symbol lookup, prices, asset profiles |
| 4 | `risk_assessment` | X-Ray analysis, diversification |
| 5 | `benchmark_comparison` | Portfolio vs index performance |
| 6 | `dividend_analysis` | Dividend income tracking |
| 7 | `account_summary` | Multi-account overview |
| 8 | `create_order` | Create a transaction (requires confirmation) |
| 9 | `delete_order` | Delete a transaction (requires confirmation) |

## Context Management

The agent uses a **sliding window** to keep the LLM context bounded. On every request, the full chat history is assembled and then trimmed to the most recent `MAX_HISTORY_MESSAGES` messages (default: **50**, ~25 conversation turns).

This prevents:
- Context window overflow on long conversations
- Unnecessary token spend on stale history

The constant `MAX_HISTORY_MESSAGES` is defined in `src/main.py` and can be adjusted as needed. When trimming occurs, a log line is emitted and the `messages_trimmed` count is included in the LangSmith run metadata.

## Running

```bash
cd agent
pip install -e .
uvicorn src.main:app --reload --port 8000
```

## Tests

```bash
cd agent
python -m pytest tests/ -v
```
