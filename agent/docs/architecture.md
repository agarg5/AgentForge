# AgentForge — Agent Architecture Document

## Domain & Use Cases

AgentForge is an AI agent for [Ghostfolio](https://ghostfol.io), an open-source wealth management platform. The agent provides natural language portfolio analysis on top of Ghostfolio's existing REST API.

**Why finance?** Portfolio management involves structured data (holdings, transactions, performance metrics) that must be presented accurately. A wrong number in a financial context is more damaging than a vague answer, making this an ideal domain for verification-focused agent development.

**Use cases supported:**
- Portfolio analysis — holdings, allocation, value, performance over time
- Transaction management — view history, create/delete orders with confirmation
- Market data — symbol lookup, current prices, asset profiles
- Risk assessment — Ghostfolio X-Ray diversification analysis
- Benchmark comparison — portfolio vs index performance
- Dividend tracking — income analysis across holdings
- Account management — multi-account overview and balances
- User preferences — persistent memory across sessions (currency, risk tolerance)

## Agent Architecture

**Framework:** LangChain + LangGraph (Python)
**LLM:** GPT-4o (temperature=0 for deterministic output)
**Backend:** FastAPI
**Memory:** Redis (chat history + user preferences)
**Deployment:** Railway (Ghostfolio + PostgreSQL + Redis + Agent API)

### Request Flow

```
User message (via Angular chat UI or API)
  -> FastAPI /chat endpoint
  -> Load chat history (from request body or Redis)
  -> Sliding window trim (max 50 messages)
  -> LangGraph ReAct agent (GPT-4o + 12 tools)
     -> Tool calls hit Ghostfolio REST API via async HTTP client
     -> Agent observes results and chains additional calls as needed
  -> Verification layer (5 checks)
  -> Persist messages to Redis
  -> Return response + metrics (tokens, cost, latency, verification results)
```

### Reasoning Approach

The agent uses a **ReAct** (Reasoning + Action) loop via LangGraph's `create_react_agent`. The system prompt includes explicit chain-of-thought instructions:
- Break complex queries into sub-tasks before calling tools
- Explain *why* each tool was selected
- Plan multi-step tool chains upfront (e.g., portfolio + benchmark + dividends)
- Handle tool failures gracefully with explanations

A **recursion limit** (25 steps) prevents runaway tool-call loops, with a user-friendly error message if hit.

### Tool Design (12 tools)

| Tool | Type | Ghostfolio API | Parameters |
|------|------|---------------|------------|
| `portfolio_analysis` | Read | `/portfolio/details`, `/performance` | range |
| `transaction_history` | Read | `/order` | accounts, asset_classes, take |
| `market_data` | Read | `/symbol/lookup`, `/symbol/:ds/:sym` | query, data_source |
| `risk_assessment` | Read | `/portfolio/report` | — |
| `benchmark_comparison` | Read | `/benchmarks` | range |
| `dividend_analysis` | Read | `/portfolio/dividends` | range |
| `account_summary` | Read | `/account` | — |
| `create_order` | Write | `POST /order` | symbol, type, quantity, price, fee, currency, date |
| `delete_order` | Write | `DELETE /order/:id` | order_id |
| `get_user_preferences` | Memory | Redis | key (optional) |
| `save_user_preference` | Memory | Redis | key, value |
| `delete_user_preference` | Memory | Redis | key |

**Design decisions:**
- All tools return formatted markdown strings (not raw JSON) so the LLM can present them directly
- Error handling at the tool level — tools catch `GhostfolioAPIError` and return error strings rather than raising exceptions
- Write operations (`create_order`, `delete_order`) include ticker verification at call time and require explicit user confirmation enforced by the system prompt

## Verification Strategy

Five verification checks run post-agent on every response:

| # | Check | What it does | Action on failure |
|---|-------|-------------|-------------------|
| 1 | **Scope** | Detects off-topic responses via weighted keyword matching (unambiguous financial terms score 2, ambiguous terms score 1, threshold of 3) | Logs warning |
| 2 | **Disclaimer** | Pattern-matches for financial disclaimers when analysis tools were used | Auto-appends disclaimer |
| 3 | **Numeric Consistency** | Cross-references numbers in the response against raw tool outputs; flags if >50% of numbers are unmatched | Logs warning |
| 4 | **Confidence Scoring** | Scores 0.0-1.0 based on tools called, data returned, hedging language, and errors | Appends low-confidence caveat if < 0.4 |
| 5 | **Ticker Verification** | Validates symbols via Ghostfolio profile lookup + search fallback (enforced at tool-call time for write operations) | Blocks invalid orders, suggests alternatives |

**Why these checks?** Financial data must not be fabricated (numeric consistency), users must know this isn't financial advice (disclaimer), the agent must stay in scope (scope check), users should know when data is uncertain (confidence), and orders must reference real securities (ticker verification).

## Eval Results

**137 total test cases** across 4 datasets:

| Dataset | Cases | Purpose |
|---------|-------|---------|
| `cases.json` | 69 | Core functional evals (tool routing, formatting, edge cases, hallucination) |
| `golden_set.yaml` | 26 | Curated rubrics with must_contain / must_not_contain criteria |
| `preference_cases.json` | 22 | Memory/preference persistence scenarios |
| `guardrails_cases.json` | 20 | Adversarial inputs (jailbreaks, prompt injection, off-topic) |

**Breakdown by category:**
- 20+ happy path (portfolio, transactions, market data, dividends, accounts, benchmarks, risk)
- 10+ edge cases (missing data, invalid input, boundary conditions)
- 26+ adversarial (20 guardrails + 6 in core cases)
- 10+ multi-step reasoning scenarios

**6 automated scorers** (via Braintrust):
- `ToolsMatch` — expected tools were called
- `MustContain` — required phrases present
- `MustNotContain` — banned phrases absent
- `ScopeDeclined` — off-topic requests properly declined
- `NoHallucination` — no fabrication indicators in tool-backed responses
- `Factuality` — LLM-as-judge scoring against expected behavior

## Observability Setup

**Tool:** LangSmith (native LangChain integration)

| Capability | Implementation |
|------------|---------------|
| Trace Logging | Full traces per request: input -> reasoning -> tool calls -> output |
| Latency Tracking | `latency_seconds` in response metrics |
| Token Usage | Input/output token counts + cost (USD) per request |
| Error Tracking | Structured logging with run_id correlation |
| User Feedback | `POST /feedback` endpoint links thumbs up/down to LangSmith traces |
| Eval Results | Braintrust dashboard with historical scores |

**Metrics exposed per request:**
```json
{
  "input_tokens": 1250,
  "output_tokens": 340,
  "total_tokens": 1590,
  "tool_call_count": 2,
  "tools_used": ["portfolio_analysis", "benchmark_comparison"],
  "latency_seconds": 3.42,
  "cost": {"total_cost_usd": 0.006525},
  "verification": [{"name": "scope", "passed": true}, ...]
}
```

## Open Source Contribution

AgentForge is published as a public GitHub repository ([agarg5/AgentForge](https://github.com/agarg5/AgentForge)) and listed as a [Ghostfolio community project](https://github.com/topics/ghostfolio) via the `ghostfolio` topic. The repository contains:
- The complete agent package (`agent/` directory) with all tools, verification, memory, and observability
- 137-case evaluation dataset (`agent/evals/datasets/`)
- Braintrust eval runner for reproducible evaluation
- Integration with Ghostfolio's existing Angular frontend (chat UI)
- Deployment configuration for Railway
