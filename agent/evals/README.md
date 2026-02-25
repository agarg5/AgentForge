# AgentForge Evaluation Framework

Standalone eval runner with rule-based scorers. Results print to the console;
traces are captured by LangSmith for observability.

## Datasets

| Dataset | Cases | Purpose |
|---------|-------|---------|
| [cases.json](datasets/cases.json) | 82 | Core functional evals - tool routing, formatting, hallucination, edge cases |
| [guardrails_cases.json](datasets/guardrails_cases.json) | 20 | Adversarial evals - jailbreaks, prompt injection, social engineering, off-topic |
| [golden_set.yaml](datasets/golden_set.yaml) | 26 | Golden set - curated rubrics with `must_contain` / `must_not_contain` |
| [preference_cases.json](datasets/preference_cases.json) | 22 | Preference memory - save, retrieve, delete, apply user preferences |

## Running Evals

```bash
# Set required env vars
export AGENT_BASE_URL=https://agent-production-b7bc.up.railway.app
export AGENT_AUTH_TOKEN=<ghostfolio_jwt>

# Optional: use mock news data to avoid Alpha Vantage rate limits
export MOCK_NEWS=true

# Optional: control parallelism (default: 20)
export EVAL_MAX_CONCURRENCY=20

# Run all evals
python agent/evals/eval_runner.py
```

## Scorers

Defined in [`eval_runner.py`](eval_runner.py):

| Scorer | Applies to | Description |
|--------|-----------|-------------|
| `ToolsMatch` | All cases | Expected tools were called (or no tools for guardrail cases) |
| `MustContain` | Golden set | All required phrases appear in response (case-insensitive) |
| `MustNotContain` | Golden set | No banned phrases appear in response |
| `ScopeDeclined` | Guardrails | Agent declined off-topic/adversarial request without jailbreaking |
| `NoHallucination` | Core cases | No fabrication indicators when tools returned real data |

All scorers are deterministic rule-based checks with no external dependencies.

## Mock News Data

The market news tool supports `MOCK_NEWS=true` to return cached data instead of
calling the Alpha Vantage API (which is rate-limited to 25 requests/day on the
free tier). This is recommended for eval runs. The mock data is in
`agent/src/tools/mock_news_data.json`.

## Getting an Auth Token

1. Log in to your Ghostfolio instance
2. Go to **Settings** (gear icon) -> **Security Token**
3. Copy the token

Then exchange it for a JWT bearer token:

```bash
curl -s -X POST https://ghostfolio-production-574b.up.railway.app/api/v1/auth/anonymous \
  -H "Content-Type: application/json" \
  -d '{"accessToken":"<SECURITY_TOKEN>"}' | jq -r .authToken
```

Use the returned JWT as `AGENT_AUTH_TOKEN` when running evals.
