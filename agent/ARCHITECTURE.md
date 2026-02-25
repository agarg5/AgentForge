# AgentForge: Agent Architecture Document

## 1. System Overview

AgentForge is a production-ready AI agent for the Ghostfolio open-source wealth management platform. It provides natural language portfolio analysis, market data queries, risk assessment, and transaction management by orchestrating calls to the Ghostfolio REST API through a structured tool-calling framework.

The agent is built on LangChain/LangGraph with GPT-4o as the reasoning engine, deployed as a standalone FastAPI service that communicates with the Ghostfolio backend over an internal network.

```
                          +---------------------+
                          |   Ghostfolio UI     |
                          |   (Angular SPA)     |
                          +--------+------------+
                                   |
                          HTTP POST /chat (JWT)
                                   |
                          +--------v------------+
                          |   Agent API         |
                          |   (FastAPI)         |
                          |                     |
                          |  +---------------+  |
                          |  | LangGraph     |  |
                          |  | ReAct Agent   |  |
                          |  | (GPT-4o)      |  |
                          |  +-------+-------+  |
                          |          |          |
                          |  +-------v-------+  |
                          |  | Tool Registry |  |
                          |  | (13 tools)    |  |
                          |  +-------+-------+  |
                          |          |          |
                          |  +-------v-------+  |       +---------------+
                          |  | Ghostfolio    +--+------>| Ghostfolio    |
                          |  | API Client    |  |       | Backend       |
                          |  | (httpx)       |  |       | (NestJS)      |
                          |  +---------------+  |       +-------+-------+
                          |          |          |               |
                          |  +-------v-------+  |       +-------v-------+
                          |  | Verification  |  |       |  PostgreSQL   |
                          |  | Layer         |  |       +---------------+
                          |  +---------------+  |
                          |          |          |       +---------------+
                          |  +-------v-------+  |       |    Redis      |
                          |  | Memory Store  +--+------>| (preferences) |
                          |  +---------------+  |       +---------------+
                          |          |          |
                          |  +-------v-------+  |       +---------------+
                          |  | Observability +--+------>|  LangSmith    |
                          |  | (tracing/cost)|  |       |  (traces)     |
                          |  +---------------+  |       +---------------+
                          +---------------------+
```

## 2. Core Components

### Reasoning Engine

The agent uses OpenAI GPT-4o (`temperature=0`) via the LangChain `ChatOpenAI` wrapper. It is configured with 5 automatic retries (exponential backoff for 429 rate limits) and a 60-second request timeout. Deterministic temperature ensures reproducible, factual responses for financial data.

### Orchestrator

The agent loop is built with LangGraph's `create_react_agent`, which implements the ReAct (Reason + Act) pattern. The orchestrator receives a message history, selects tools based on the system prompt and user query, executes tool calls, observes results, and iterates until it produces a final answer. All per-request state (auth token, API client, memory store) is injected via `RunnableConfig["configurable"]`.

### Tool Registry

Thirteen tools are registered with the agent at startup. Each tool is a LangChain `@tool`-decorated async function that receives a `RunnableConfig` for dependency injection. Tools are stateless; the Ghostfolio API client and memory store are passed per-request through the config. See Section 3 for the full tool table.

### Memory System

A Redis-backed persistent preference store (`MemoryStore`) allows the agent to remember user settings across sessions. User identity is derived from a SHA-256 hash of the JWT auth token (first 16 hex characters), ensuring non-reversible keying. Each user's preferences are stored as a Redis hash map. The system falls back to an in-memory dictionary when Redis is unavailable, supporting local development without infrastructure dependencies.

### Verification Layer

A post-processing pipeline that runs three checks on every agent response before returning it to the user. It can amend responses (e.g., appending missing disclaimers) and attaches check results to the response metadata. See Section 5 for details.

### Output Formatter

The system prompt instructs the agent to format all responses using markdown tables for structured data (holdings, transactions, accounts), bullet points for summaries, and consistent numeric formatting (currency symbols, two-decimal percentages). The formatter is prompt-driven rather than code-driven, leveraging GPT-4o's instruction-following capability.

## 3. Tool Architecture

| # | Tool | Type | API Source | Description |
|---|------|------|-----------|-------------|
| 1 | `portfolio_analysis` | Read | `GET /api/v1/portfolio/details`, `GET /api/v2/portfolio/performance` | Holdings, allocation percentages, total value, net performance |
| 2 | `transaction_history` | Read | `GET /api/v1/order` | Recent buy/sell activity with date, type, symbol, quantity filters |
| 3 | `market_data` | Read | `GET /api/v1/symbol/{dataSource}/{symbol}`, `GET /api/v1/symbol/lookup` | Symbol profile lookup or fuzzy search for asset information |
| 4 | `risk_assessment` | Read | `GET /api/v1/portfolio/report` | X-Ray analysis: concentration, currency, fee, diversification warnings |
| 5 | `benchmark_comparison` | Read | `GET /api/v1/benchmarks`, `GET /api/v2/portfolio/performance` | Portfolio returns vs. configured market index benchmarks |
| 6 | `dividend_analysis` | Read | `GET /api/v1/portfolio/dividends` | Dividend income by period with yield calculation |
| 7 | `account_summary` | Read | `GET /api/v1/account` | Multi-account overview with balances and platform info |
| 8 | `market_news` | Read | Alpha Vantage News API | Financial news headlines and sentiment for market context |
| 9 | `create_order` | Write | `POST /api/v1/order` | Create a buy/sell order (requires user confirmation + ticker verification) |
| 10 | `delete_order` | Write | `DELETE /api/v1/order/{id}` | Delete an existing order by ID (requires user confirmation) |
| 11 | `get_user_preferences` | Read | Redis `HGETALL` / `HGET` | Retrieve saved user preferences for personalization |
| 12 | `save_user_preference` | Write | Redis `HSET` | Persist a user preference (currency, risk tolerance, etc.) |
| 13 | `delete_user_preference` | Write | Redis `HDEL` | Remove a saved preference |

All Ghostfolio API calls are made through `GhostfolioClient`, an async HTTP client built on `httpx.AsyncClient` with connection pooling, 30-second timeouts, and unified error handling via the `GhostfolioAPIError` exception class.

## 4. Request Lifecycle

A chat request follows this path through the system:

1. **HTTP Ingress** -- The Ghostfolio Angular frontend sends `POST /chat` with a JSON body containing the user message, conversation history, and optional session ID. The JWT bearer token is passed via the `Authorization` header.

2. **Authentication** -- The FastAPI endpoint extracts the bearer token. If missing, the request is rejected with HTTP 401.

3. **Message Assembly** -- The conversation history is converted to LangChain `HumanMessage` and `AIMessage` objects. The current user message is appended as the final `HumanMessage`.

4. **Config Construction** -- A `RunnableConfig` is built with: a unique `run_id` (UUID), LangSmith metadata and tags, and a `configurable` dict containing the `GhostfolioClient` (instantiated with the user's JWT), the `MemoryStore`, and the auth token.

5. **Agent Execution** -- `agent.ainvoke()` runs the ReAct loop. The LLM receives the system prompt, message history, and tool schemas. It reasons about which tools to call, executes them (potentially multiple rounds), and produces a final text response.

6. **Metrics Extraction** -- Token usage (input/output/total), tool call count, and tool names are extracted from the result message objects. Total latency is measured via `time.monotonic()`, and a `TimingCallback` (LangChain callback handler) tracks LLM call time vs tool execution time separately. Per-request cost is calculated from token counts and GPT-4o pricing.

7. **Verification** -- The final AI message and raw tool outputs are passed through the verification layer. Checks run for disclaimer presence, numeric consistency, and ticker validity. The response may be amended (e.g., a disclaimer appended).

8. **Response** -- A `ChatResponse` is returned containing the (possibly amended) text, the `run_id` (for feedback linking), and a metrics dict with latency, token usage, cost breakdown, and verification check results.

## 5. Verification Layer

The verification layer (`verify_response`) is a post-processing pipeline that runs after every agent response. It is designed to be non-blocking: if any check throws an exception, it is caught and logged, and the response is returned unmodified.

| Check | Trigger | Behavior |
|-------|---------|----------|
| **Disclaimer** | Response uses a financial analysis tool (`portfolio_analysis`, `benchmark_comparison`, `risk_assessment`, `dividend_analysis`) | Scans the response for disclaimer phrases via regex (e.g., "not financial advice", "informational purposes"). If absent, appends a standard disclaimer to the response. |
| **Numeric Consistency** | Tool outputs contain significant numbers (2+ digits) | Extracts all significant numbers from the response and cross-references them against raw tool output strings. Flags the response if >50% of numbers (minimum 2) are not found in tool outputs, indicating potential hallucination. |
| **Ticker Verification** | `create_order` tool is called | Enforced at tool-call time (upstream). Before creating an order, the tool calls `verify_ticker`, which attempts a direct symbol profile lookup via the Ghostfolio API and falls back to a fuzzy search. Invalid symbols are rejected with suggestions. |

## 6. Observability

### LangSmith Tracing

When environment variables `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set, every agent invocation is traced to LangSmith. Each trace includes:

- A unique `run_id` (UUID) for correlation
- Tags (`agentforge`, `chat`) for filtering
- Metadata: session ID, message length
- Full LLM input/output, tool calls, and intermediate reasoning steps

### Per-Request Metrics

Every response includes a `metrics` object:

```json
{
  "latency_seconds": 2.341,
  "latency_breakdown": {
    "llm_seconds": 1.842,
    "tool_seconds": 0.389
  },
  "input_tokens": 1520,
  "output_tokens": 430,
  "total_tokens": 1950,
  "tool_call_count": 2,
  "tools_used": ["portfolio_analysis", "benchmark_comparison"],
  "cost": {
    "model": "gpt-4o",
    "input_cost_usd": 0.0038,
    "output_cost_usd": 0.0043,
    "total_cost_usd": 0.0081
  },
  "verification": [...]
}
```

Cost is calculated using GPT-4o pricing: $2.50 per 1M input tokens, $10.00 per 1M output tokens. A `calculate_batch_cost` function supports aggregate cost analysis across multiple requests.

### User Feedback

The `POST /feedback` endpoint accepts a `run_id`, a numeric score (1.0 = positive, 0.0 = negative), and an optional comment. Feedback is submitted to LangSmith via its Python SDK, linking it to the corresponding trace for analysis in the LangSmith dashboard.

## 7. Deployment Architecture

The system is deployed on Railway as four services within a single project:

```
+------------------------------------------------------------------+
|  Railway Project: ghostfolio-agentforge                          |
|                                                                  |
|  +------------------+     +------------------+                   |
|  |  Ghostfolio      |     |  Agent API       |                   |
|  |  (NestJS)        |<----|  (FastAPI)        |                   |
|  |  Port 3333       |     |  Port 8000        |                   |
|  +--------+---------+     +------------------+                   |
|           |                                                      |
|  +--------v---------+     +------------------+                   |
|  |  PostgreSQL      |     |  Redis           |                   |
|  |  (Prisma ORM)    |     |  (preferences)   |                   |
|  +------------------+     +------------------+                   |
+------------------------------------------------------------------+
```

| Service | Role | Internal Address |
|---------|------|-----------------|
| Ghostfolio | NestJS backend, Angular frontend, Prisma ORM | `ghostfolio.railway.internal:3333` |
| Agent API | FastAPI agent service, Dockerfile-based | `agent.railway.internal:8000` |
| PostgreSQL | Primary data store for Ghostfolio (users, orders, portfolios) | Managed Railway Postgres |
| Redis | User preference persistence, Ghostfolio caching | Managed Railway Redis |

The Agent API communicates with Ghostfolio over Railway's internal network (`GHOSTFOLIO_BASE_URL=http://ghostfolio.railway.internal:3333`), avoiding public internet round-trips. The Ghostfolio frontend proxies chat requests to the Agent API via a configured `AGENT_API_URL`.

## 8. Security

### JWT Authentication Pass-Through

The agent does not manage its own authentication. The Ghostfolio frontend obtains a JWT via `POST /api/v1/auth/anonymous` and passes it to the agent API in the `Authorization: Bearer` header. The agent forwards this token to all Ghostfolio API calls, ensuring that each user can only access their own portfolio data. The token is never logged or persisted in plaintext; the memory store uses a one-way SHA-256 hash of the token as the user key.

### Write Operation Confirmation Gates

The system prompt explicitly instructs the agent to never execute write operations (`create_order`, `delete_order`) without prior user confirmation. This is enforced at two levels:

1. **Prompt-level** -- The system prompt mandates that the agent describe the pending action in detail and wait for explicit user confirmation before calling any write tool.
2. **Tool-level** -- The `create_order` and `delete_order` tool docstrings include the directive that the agent "MUST have received explicit user confirmation before calling this tool," which is included in the tool schema sent to the LLM.

### Input Validation

Write tools enforce parameter validation before API calls: `create_order` validates that quantity is positive, unit price is non-negative, and order type is one of the allowed values (BUY, SELL, DIVIDEND, FEE, INTEREST, LIABILITY). Ticker symbols are verified against the Ghostfolio data source before order creation.

### Error Isolation

All Ghostfolio API errors are caught and converted to user-friendly error messages via the `GhostfolioAPIError` exception class. Verification layer exceptions are caught individually so that a failing check never blocks the response. Agent-level exceptions return a generic error message with the `run_id` for debugging.
