# AgentForge Evaluation Framework

Three eval datasets tested via a unified [Braintrust](https://braintrust.dev) runner.

## Datasets

| Dataset | Cases | Purpose |
|---------|-------|---------|
| [cases.json](datasets/cases.json) | 69 | Core functional evals — tool routing, formatting, hallucination, edge cases |
| [guardrails_cases.json](datasets/guardrails_cases.json) | 20 | Adversarial evals — jailbreaks, prompt injection, social engineering, off-topic |
| [golden_set.yaml](datasets/golden_set.yaml) | 20 | Golden set — curated rubrics with `must_contain` / `must_not_contain` / `expected_behavior` |

## Running Evals

All datasets are run through a single Braintrust entry point ([`bt_eval.py`](bt_eval.py)):

```bash
# Set required env vars
export BRAINTRUST_API_KEY=<key>        # Get one at braintrust.dev
export AGENT_BASE_URL=https://agent-production-b7bc.up.railway.app
export AGENT_AUTH_TOKEN=<ghostfolio_jwt>

# Run all evals (uploads results to Braintrust dashboard)
braintrust eval agent/evals/bt_eval.py

# Or run directly
python agent/evals/bt_eval.py
```

## Scorers

Defined in [`bt_eval.py`](bt_eval.py):

| Scorer | Applies to | Description |
|--------|-----------|-------------|
| `ToolsMatch` | All cases | Expected tools were called (or no tools for guardrail cases) |
| `MustContain` | Golden set | All required phrases appear in response (case-insensitive) |
| `MustNotContain` | Golden set | No banned phrases appear in response |
| `ScopeDeclined` | Guardrails | Agent declined off-topic/adversarial request without jailbreaking |
| `NoHallucination` | Core cases | No fabrication indicators when tools returned real data |
| `Factuality` | Golden set | LLM-as-judge scoring against `expected_behavior` (via [autoevals](https://github.com/braintrustdata/autoevals)) |

## Golden Set Format

Each golden set case includes a content-quality rubric:

```yaml
- id: golden-portfolio-001
  category: portfolio_analysis
  query: "What is my portfolio worth right now?"
  expected_tools: [portfolio_analysis]
  must_contain:
    - "portfolio"
  must_not_contain:
    - "hypothetical"
    - "for example, let's say"
    - "I don't have access"
  expected_behavior: >
    Should call portfolio_analysis, return the total portfolio value
    with a currency symbol/code, and base numbers on actual tool output.
```

## Getting an Auth Token

1. Log in to your Ghostfolio instance
2. Go to **Settings** (gear icon) → **Security Token**
3. Copy the token — this is your `GHOSTFOLIO_ACCESS_TOKEN`

Then exchange it for a JWT bearer token:

```bash
curl -s -X POST https://ghostfolio-production-574b.up.railway.app/api/v1/auth/anonymous \
  -H "Content-Type: application/json" \
  -d '{"accessToken":"<GHOSTFOLIO_ACCESS_TOKEN>"}' | jq -r .authToken
```

Use the returned JWT as `AGENT_AUTH_TOKEN` when running evals.
