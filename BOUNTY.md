# Congressional Stock Trading Tool

## Overview

A full-stack feature that lets users explore stock trades made by members of the U.S. Congress directly from the chat interface. Users can click on politician profile cards or ask natural language questions to see what Congress is buying and selling.

## What was built

### 1. Congressional Trades LangChain Tool (`agent/src/tools/congressional_trades.py`)

A new AI agent tool that fetches and filters real congressional stock trading data from the [Quiver Quantitative API](https://www.quiverquant.com/congresstrading/).

**Capabilities:**
- Filter trades by **politician name** (e.g., "Show me Pelosi's trades")
- Filter by **chamber** (Senate or House)
- Filter by **stock ticker** (e.g., "Who in Congress is trading NVDA?")
- Configurable **date range** (default: last 90 days)
- Returns formatted markdown tables with politician, party, ticker, transaction type, amount, and dates
- Mock mode (`MOCK_CONGRESS=true`) for offline testing and evals

**Data source:** Quiver Quantitative API (`/beta/live/congresstrading`) with Bearer token auth.

### 2. Politician Quick-Access Cards (Angular Chat UI)

Interactive profile cards on the chat welcome screen showing notable congressional traders with:
- **Official congressional photos** from bioguide.congress.gov (public domain)
- **Party-colored borders** (blue for Democrats, red for Republicans)
- **One-click access** — clicking a card sends "Show me [Name]'s recent stock trades"

**Politicians featured:**
| Name | Chamber | Party |
|------|---------|-------|
| Nancy Pelosi | House | D |
| Tommy Tuberville | Senate | R |
| Marjorie Taylor Greene | House | R |
| Dan Crenshaw | House | R |
| Ro Khanna | House | D |
| Markwayne Mullin | Senate | R |

### 3. Full-Stack API Wiring

- **FastAPI endpoint** (`GET /api/politicians`) serves the politician list with photo URLs
- **NestJS proxy** (`GET /api/v1/ai/politicians`) forwards to the agent service with JWT auth
- **Angular data service** (`getPoliticians()`) fetches and renders the cards
- Tool registered in the LangChain agent with system prompt guidance

## Architecture

```
User clicks politician card
  → Angular sends chat message: "Show me Nancy Pelosi's recent stock trades"
    → NestJS forwards to Agent API
      → LangChain agent invokes congressional_trades tool
        → Tool calls Quiver API with Bearer token
          → Filters by politician name, formats as markdown table
        → Agent returns formatted response to user
```

## Files changed

| File | Description |
|------|-------------|
| `agent/src/tools/congressional_trades.py` | LangChain tool (Quiver API integration) |
| `agent/src/tools/mock_congressional_trades.json` | 20 mock trades for testing |
| `agent/src/agent.py` | Registered tool in agent |
| `agent/src/prompts/system.py` | Added congressional trading guidance |
| `agent/src/main.py` | FastAPI `/api/politicians` endpoint |
| `agent/tests/test_tools.py` | 5 unit tests |
| `agent/evals/datasets/cases.json` | 5 eval cases |
| `apps/api/src/app/endpoints/ai/ai.controller.ts` | NestJS proxy endpoint |
| `apps/api/src/app/endpoints/ai/ai.service.ts` | NestJS service method |
| `apps/client/src/app/pages/chat/chat-page.component.ts` | Angular component (cards logic) |
| `apps/client/src/app/pages/chat/chat-page.html` | Card template with photos |
| `apps/client/src/app/pages/chat/chat-page.scss` | Card styles (party colors, dark mode) |
| `libs/ui/src/lib/services/data.service.ts` | Angular data service |

## Testing

### Unit tests
```bash
cd agent && .venv/bin/python -m pytest tests/test_tools.py -v -k congressional
# 5 tests: success, by_politician, by_ticker, empty, error
```

### Example queries
- "Show me Nancy Pelosi's recent stock trades"
- "What stocks is Congress buying?"
- "Who in Congress is trading NVDA?"
- "Show me Senate trades from the last 30 days"
- "What has Tommy Tuberville been trading?"

## Environment variables

| Variable | Description |
|----------|-------------|
| `QUIVER_AUTHORIZATION_TOKEN` | Quiver Quantitative API Bearer token |
| `MOCK_CONGRESS` | Set to `true` for mock data in tests/evals |

## PRs

- [#52](https://github.com/agarg5/AgentForge/pull/52) — Initial implementation (tool, UI, tests, evals)
- [#53](https://github.com/agarg5/AgentForge/pull/53) — Use targeted API endpoints for latency
- [#54](https://github.com/agarg5/AgentForge/pull/54) — Add Accept header fix, revert to single working endpoint
- [#55](https://github.com/agarg5/AgentForge/pull/55) — Widen cards, add Marjorie Taylor Greene
