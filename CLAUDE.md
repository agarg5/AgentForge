# AgentForge — Ghostfolio Finance Agent

## Project Overview
Building a production-ready AI agent for the Ghostfolio wealth management platform. The agent provides natural language portfolio analysis, market data queries, risk assessment, and financial guidance.

## Tech Stack
- **Agent Framework:** LangChain (Python)
- **LLM:** GPT-4o (OpenAI API key in `$OPENAI_API_KEY`)
- **Observability:** LangSmith
- **Backend:** Python/FastAPI for agent API layer
- **Frontend:** Next.js or Streamlit for rapid prototyping
- **Database:** Ghostfolio's PostgreSQL (via Ghostfolio REST API)
- **Deployment:** Railway (Ghostfolio backend + PostgreSQL + Redis + agent API)

## Repository Structure
```
AgentForge/                    # Forked Ghostfolio repo (NestJS + Angular)
├── apps/api/                  # Ghostfolio NestJS backend
├── apps/client/               # Ghostfolio Angular frontend
├── prisma/                    # Database schema
├── agent/                     # Our AI agent (NEW)
│   ├── src/
│   │   ├── tools/             # LangChain tool definitions
│   │   ├── verification/      # Verification layer
│   │   ├── prompts/           # System prompts
│   │   └── api/               # FastAPI endpoints
│   ├── evals/                 # Evaluation framework
│   │   ├── datasets/          # Test cases (50+)
│   │   └── runners/           # Eval execution
│   ├── observability/         # LangSmith configuration
│   └── tests/                 # Unit + integration tests
```

## Agent Tools (7 tools)
1. `portfolio_analysis` — Holdings, allocation, performance
2. `transaction_history` — Activity list with filters
3. `market_data` — Symbol lookup, prices, asset profiles
4. `risk_assessment` — X-Ray analysis, diversification
5. `benchmark_comparison` — Portfolio vs index performance
6. `dividend_analysis` — Dividend income tracking
7. `account_summary` — Multi-account overview

## Key Ghostfolio API Endpoints
- `GET /api/v1/portfolio/details` — Portfolio overview
- `GET /api/v1/portfolio/performance` — Performance metrics
- `GET /api/v1/portfolio/report` — X-Ray risk analysis
- `GET /api/v1/portfolio/dividends` — Dividend data
- `GET /api/v1/order` — Transaction list
- `GET /api/v1/account` — Account list
- `GET /api/v1/symbol/:dataSource/:symbol` — Market data
- `GET /api/v1/symbol/lookup` — Symbol search
- `GET /api/v1/benchmarks` — Benchmark list

## Authentication
Ghostfolio uses JWT bearer tokens:
```
POST /api/v1/auth/anonymous → { "accessToken": "<token>" }
Returns: { "authToken": "eyJh..." }
Header: "Authorization: Bearer <authToken>"
```

## Development Workflow
- Use git worktrees for feature branches
- Run evals before merging any changes
- LangSmith traces for all agent interactions
- Deploy to Railway for public access

## Running Tests & Evals

### Unit tests (offline, no API calls)
```bash
cd agent && .venv/bin/python -m pytest tests/ -v
```
230 tests, 2 pre-existing failures in test_tools.py (unrelated to agent logic).

### Live evals against deployed agent (Braintrust)
```bash
cd agent

# 1. Get a Ghostfolio auth token
export SECURITY_TOKEN="<from Ghostfolio Settings → Security Token>"
export AGENT_AUTH_TOKEN=$(curl -s -X POST "https://ghostfolio-production-574b.up.railway.app/api/v1/auth/anonymous" \
  -H "Content-Type: application/json" \
  -d "{\"accessToken\": \"$SECURITY_TOKEN\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['authToken'])")

# 2. Run evals (results go to braintrust.dev dashboard)
export BRAINTRUST_API_KEY="<from braintrust.dev>"
export AGENT_BASE_URL="https://agent-production-b7bc.up.railway.app"
.venv/bin/python evals/bt_eval.py
```

### Eval datasets (150 total cases)
- `evals/datasets/cases.json` — 82 core functional cases
- `evals/datasets/guardrails_cases.json` — 20 adversarial/jailbreak cases
- `evals/datasets/golden_set.yaml` — 26 curated rubric cases
- `evals/datasets/preference_cases.json` — 22 preference memory cases

### Assignment performance targets
- Single-tool latency: <5s
- Multi-step latency: <15s
- Tool success rate: >95%
- Eval pass rate: >80%
- Hallucination rate: <5%
- Verification accuracy: >90%

## Chat in Production (Railway)
For `/en/chat` to work, deploy the **Agent** as a separate Railway service and set **AGENT_API_URL** on the Ghostfolio API to the agent’s URL. See `agent/RAILWAY_DEPLOYMENT.md`.

## Verification Rules
- All ticker symbols must resolve to real securities
- Portfolio values must match Ghostfolio's computed values
- Financial advice must include disclaimers
- Market data must be sourced (no fabrication)
- Portfolio modifications require explicit user confirmation

## Build Priority
1. Basic agent — single tool call working end-to-end
2. Tool expansion — add remaining tools, verify each
3. Multi-step reasoning — agent chains tools
4. Observability — LangSmith tracing
5. Eval framework — 50+ test cases
6. Verification layer — domain-specific checks
7. Iterate on evals — improve based on failures
8. Open source prep — package and document
