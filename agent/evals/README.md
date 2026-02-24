# AgentForge Evaluation Framework

Three evaluation suites that test the agent across different dimensions.

## Datasets

| Dataset | Cases | Purpose |
|---------|-------|---------|
| [cases.json](datasets/cases.json) | 60+ | Core functional evals — tool routing, formatting, hallucination, edge cases |
| [guardrails_cases.json](datasets/guardrails_cases.json) | 20 | Adversarial evals — jailbreaks, prompt injection, social engineering, off-topic |
| [golden_set.yaml](datasets/golden_set.yaml) | 22 | Golden set — curated rubrics with `must_contain` / `must_not_contain` / `expected_behavior` |

## Runners

### Core evals (`cases.json`)

```bash
# Validate dataset structure (no agent needed)
python -m evals.runners.eval_runner --dry-run

# Run against live agent
python -m evals.runners.eval_runner \
  --base-url https://agent-production-b7bc.up.railway.app \
  --token <ghostfolio_auth_token>
```

### Guardrails evals (`guardrails_cases.json`)

Tests hostile, off-topic, and jailbreak prompts across multiple attack vectors.

```bash
python -m evals.test_guardrails \
  --base-url https://agent-production-b7bc.up.railway.app \
  --token <ghostfolio_auth_token> \
  --output guardrails_results.json
```

### Golden set evals (`golden_set.yaml`)

Content-quality rubrics with `must_contain` / `must_not_contain` checks.

```bash
python -m evals.test_golden \
  --base-url https://agent-production-b7bc.up.railway.app \
  --token <ghostfolio_auth_token> \
  --output golden_results.json
```

## Assertion Checks

Defined in [`checks/assertions.py`](checks/assertions.py):

| Check | Description |
|-------|-------------|
| `tool_called` | At least one expected tool was invoked |
| `multi_tool_called` | At least 2 expected tools invoked |
| `no_tool_called` | No tools were invoked |
| `no_hallucination` | No fabrication indicators in response |
| `values_from_tool` | Numeric values in response match tool output |
| `contains_table` | Response has markdown table formatting |
| `contains_currency` | Response mentions a currency symbol/code |
| `contains_percentage` | Response contains a percentage value |
| `has_disclaimer` | Response includes financial disclaimer |
| `scope_declined` | Agent declined an off-topic request |
| `must_contain_all` | All required phrases appear in response |
| `must_not_contain_any` | No banned phrases appear in response |

## Getting an Auth Token

```bash
curl -s -X POST https://ghostfolio-production-574b.up.railway.app/api/v1/auth/anonymous \
  -H "Content-Type: application/json" \
  -d '{"accessToken":"<GHOSTFOLIO_ACCESS_TOKEN>"}' | jq -r .authToken
```
