# AgentForge — AI Cost Analysis

## Development & Testing Costs

### LLM API Costs (GPT-4o)

| Metric | Value |
|--------|-------|
| Model | GPT-4o |
| Input price | $2.50 / 1M tokens |
| Output price | $10.00 / 1M tokens |

**Estimated development spend:**

| Activity | Requests | Avg Input Tokens | Avg Output Tokens | Cost |
|----------|----------|-----------------|-------------------|------|
| Manual testing & iteration | ~200 | ~1,500 | ~400 | ~$1.55 |
| Eval runs (137 cases x ~3 runs) | ~411 | ~1,200 | ~350 | ~$2.67 |
| LLM-as-judge (Factuality scorer) | ~78 | ~800 | ~200 | ~$0.31 |
| **Total development** | **~689** | | | **~$4.53** |

### Token Breakdown

| Category | Input Tokens | Output Tokens | Total Tokens |
|----------|-------------|---------------|-------------|
| Development testing | ~300,000 | ~80,000 | ~380,000 |
| Eval runs | ~493,200 | ~143,850 | ~637,050 |
| Factuality scoring | ~62,400 | ~15,600 | ~78,000 |
| **Total** | **~855,600** | **~239,450** | **~1,095,050** |

### Infrastructure Costs

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Railway — Ghostfolio | $5 (Hobby plan) | NestJS backend + build minutes |
| Railway — PostgreSQL | Included | Hobby plan covers small DBs |
| Railway — Redis | Included | Chat history + preferences |
| Railway — Agent API | Included | FastAPI service |
| LangSmith | Free tier | Tracing and eval dashboard |
| Braintrust | Free tier | Eval runner and scoring |
| **Total infrastructure** | **~$5/month** | |

## Production Cost Projections

### Assumptions

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Queries per user per day | 5 | Typical portfolio check-in frequency |
| Avg input tokens per query | 1,500 | System prompt (~600) + history (~600) + user message (~300) |
| Avg output tokens per query | 400 | Response with markdown table + explanation |
| Avg tool calls per query | 1.5 | Most queries need 1-2 tools |
| Verification overhead | Negligible | Regex-based checks, no LLM calls |
| Days per month | 30 | |

### Per-Query Cost

| Component | Tokens | Cost |
|-----------|--------|------|
| Input (system prompt + history + message) | 1,500 | $0.00375 |
| Output (response) | 400 | $0.00400 |
| **Total per query** | **1,900** | **$0.00775** |

### Monthly Projections

| | 100 Users | 1,000 Users | 10,000 Users | 100,000 Users |
|---|-----------|-------------|--------------|---------------|
| Queries/month | 15,000 | 150,000 | 1,500,000 | 15,000,000 |
| Input tokens | 22.5M | 225M | 2.25B | 22.5B |
| Output tokens | 6M | 60M | 600M | 6B |
| **LLM cost** | **$116/mo** | **$1,163/mo** | **$11,625/mo** | **$116,250/mo** |
| Infrastructure (Railway) | $20/mo | $50/mo | $200/mo | $1,000/mo |
| Observability (LangSmith) | Free | $39/mo | $39/mo | Custom |
| **Total** | **$136/mo** | **$1,252/mo** | **$11,864/mo** | **~$117,250/mo** |

### Cost Optimization Strategies

| Strategy | Savings | Trade-off |
|----------|---------|-----------|
| **Switch to GPT-4o-mini** ($0.15/$0.60 per 1M) | ~94% LLM cost reduction | Slightly lower reasoning quality |
| **Cache common queries** (e.g., "show my portfolio") | 20-40% fewer API calls | Stale data risk (mitigate with TTL) |
| **Reduce system prompt** (currently ~600 tokens) | ~5% input cost reduction | Less instruction detail |
| **Trim history more aggressively** (25 messages vs 50) | ~15% input cost reduction | Shorter conversational memory |
| **Batch tool calls** where possible | Fewer LLM round-trips | Requires orchestrator changes |

### GPT-4o-mini Projection (optimized)

If using GPT-4o-mini for all queries:

| | 100 Users | 1,000 Users | 10,000 Users | 100,000 Users |
|---|-----------|-------------|--------------|---------------|
| **LLM cost** | **$7/mo** | **$70/mo** | **$697/mo** | **$6,975/mo** |

This makes the agent viable at scale — 10,000 users for under $1,000/month in LLM costs.
