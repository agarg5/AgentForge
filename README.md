# AgentForge

AI-powered financial assistant for [Ghostfolio](https://github.com/ghostfolio/ghostfolio), an open source wealth management platform. Ask natural language questions about your portfolio and get answers backed by real data.

## What it does

AgentForge adds a conversational AI layer on top of Ghostfolio. It connects to your Ghostfolio instance, calls the right APIs, and returns grounded answers — no hallucinated numbers.

**9 tools** wrapping the Ghostfolio REST API:

| Tool | Description |
|------|-------------|
| `portfolio_analysis` | Holdings, allocation, performance |
| `transaction_history` | Activity list with filters |
| `market_data` | Symbol lookup, prices, asset profiles |
| `risk_assessment` | X-Ray analysis, diversification |
| `benchmark_comparison` | Portfolio vs index performance |
| `dividend_analysis` | Dividend income tracking |
| `account_summary` | Multi-account overview |
| `create_order` | Create orders (requires confirmation) |
| `delete_order` | Delete orders (requires confirmation) |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Ghostfolio UI  │────▶│  Agent API       │────▶│  Ghostfolio API │
│  (Angular)      │     │  (FastAPI/Python) │     │  (NestJS)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                         ┌────┴────┐
                         │  GPT-4o │
                         └─────────┘
```

- **Agent**: LangChain + GPT-4o with tool calling
- **Backend**: FastAPI serving the agent API
- **Observability**: LangSmith tracing on every request
- **Verification**: Post-response checks for disclaimers, numeric consistency, ticker validation
- **Memory**: Persistent user preferences via Redis

## Repository Structure

```
agent/                     # AI agent (Python)
├── src/
│   ├── tools/             # LangChain tool definitions (9 tools)
│   ├── verification/      # Post-response verification layer
│   ├── prompts/           # System prompts with guardrails
│   ├── memory/            # Persistent preference store
│   └── client.py          # Ghostfolio API client
├── evals/                 # Evaluation framework (see evals/README.md)
│   ├── datasets/          # Test cases (90+ across 3 datasets)
│   └── bt_eval.py         # Braintrust eval runner
└── tests/                 # Unit tests

apps/api/                  # Ghostfolio NestJS backend (upstream)
apps/client/               # Ghostfolio Angular frontend (with chat UI)
prisma/                    # Database schema
```

## Deployment

Both services run on Railway:

| Service | URL |
|---------|-----|
| Ghostfolio | `https://ghostfolio-production-574b.up.railway.app` |
| Agent API | `https://agent-production-b7bc.up.railway.app` |

## Evals

Three eval suites with 90+ test cases. See [`agent/evals/README.md`](agent/evals/README.md) for details.

| Dataset | Cases | Purpose |
|---------|-------|---------|
| `cases.json` | 69 | Core functional evals |
| `guardrails_cases.json` | 20 | Adversarial / jailbreak evals |
| `golden_set.yaml` | 20 | Content-quality rubrics |

## Guardrails

- Scoped to portfolio/financial topics only — off-topic requests are declined
- Write operations (create/delete orders) require explicit user confirmation
- System prompt injection and jailbreak resistant (tested across 6 languages)
- All responses include financial disclaimers
- No fabricated data — values come from tool output or the agent says so honestly

## Open Source Contribution

We contributed a bug fix back to the upstream Ghostfolio project:

- **PR [ghostfolio/ghostfolio#6397](https://github.com/ghostfolio/ghostfolio/pull/6397)** — Fix X-ray rule exception when `marketPrice` is null. The `/api/v1/portfolio/report` endpoint crashed with a `[big.js] Invalid number` error when a holding had no market price data (e.g. newly added activity before price data is fetched). Fixes [#4607](https://github.com/ghostfolio/ghostfolio/issues/4607).

## License

The Ghostfolio platform is licensed under [AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html). See the upstream repo for details.
