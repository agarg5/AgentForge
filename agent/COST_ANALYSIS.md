# AgentForge AI Cost Analysis

This document provides a detailed breakdown of AI costs for the AgentForge financial agent, covering development spend, per-request economics, production projections, optimization strategies, and infrastructure costs.

All pricing is based on OpenAI GPT-4o rates as of January 2025, matching the values in `src/observability/cost.py`.

---

## 1. Development Spend

### Model Pricing

| Model       | Input (per 1M tokens) | Output (per 1M tokens) |
|-------------|----------------------:|------------------------:|
| GPT-4o      | $2.50                 | $10.00                  |
| GPT-4o-mini | $0.15                 | $0.60                   |

### Token Estimates

Based on typical agent interactions (system prompt + tool definitions + user query + tool call/response + final answer), the average request uses approximately:

- **Input tokens:** ~2,000 (system prompt ~400 tokens, tool schemas ~800 tokens, user message + history ~400 tokens, tool results ~400 tokens)
- **Output tokens:** ~800 (tool call arguments ~200 tokens, final response ~600 tokens)

### Development Activity

| Activity               | Requests | Input Tokens/Req | Output Tokens/Req | Total Input | Total Output |
|------------------------|----------|------------------:|-------------------:|------------:|-------------:|
| Eval runs              | 500      | 2,000             | 800                | 1,000,000   | 400,000      |
| Ad-hoc test queries    | 200      | 2,000             | 800                | 400,000     | 160,000      |
| **Total**              | **700**  |                   |                    | **1,400,000** | **560,000** |

### Development Cost Calculation

```
Input cost  = 1,400,000 / 1,000,000 * $2.50  = $3.50
Output cost =   560,000 / 1,000,000 * $10.00  = $5.60
                                        Total = $9.10
```

**Total estimated development spend: $9.10**

This is notably low, which is one advantage of using GPT-4o's competitive pricing for a tool-calling agent. Even doubling the estimate to account for retries, debugging, and failed runs, the total stays under $20.

---

## 2. Per-Request Cost Breakdown

### Single-Tool Query

A straightforward question like "What is my portfolio value?" triggers one tool call.

| Component        | Input Tokens | Output Tokens |
|------------------|-------------:|--------------:|
| System prompt    | 400          | --            |
| Tool schemas     | 800          | --            |
| User message     | 100          | --            |
| Tool call (args) | --           | 100           |
| Tool result      | 200          | --            |
| Final response   | --           | 400           |
| **Total**        | **1,500**    | **500**       |

```
Input cost  = 1,500 / 1,000,000 * $2.50  = $0.00375
Output cost =   500 / 1,000,000 * $10.00  = $0.00500
                                    Total = $0.00875
```

**Cost per single-tool query: $0.00875 (~0.9 cents)**

### Multi-Tool Query

A complex question like "Compare my portfolio performance to the S&P 500 and show my risk exposure" triggers 2-3 tool calls with a synthesized response.

| Component             | Input Tokens | Output Tokens |
|-----------------------|-------------:|--------------:|
| System prompt         | 400          | --            |
| Tool schemas          | 800          | --            |
| User message          | 200          | --            |
| Tool call 1 (args)    | --           | 150           |
| Tool result 1         | 400          | --            |
| Tool call 2 (args)    | --           | 150           |
| Tool result 2         | 600          | --            |
| Tool call 3 (args)    | --           | 100           |
| Tool result 3         | 600          | --            |
| Final response        | --           | 800           |
| **Total**             | **3,000**    | **1,200**     |

```
Input cost  = 3,000 / 1,000,000 * $2.50  = $0.00750
Output cost = 1,200 / 1,000,000 * $10.00  = $0.01200
                                    Total = $0.01950
```

**Cost per multi-tool query: $0.01950 (~2.0 cents)**

### Blended Average

Assuming a 70/30 split between single-tool and multi-tool queries:

```
Blended avg = (0.70 * $0.00875) + (0.30 * $0.01950) = $0.01198
```

**Blended average cost per request: ~$0.012 (1.2 cents)**

---

## 3. Production Cost Projections

Using the blended average of $0.012 per request and assuming 5 queries per user per day.

| DAU     | Daily Requests | Avg Cost/Req | Daily Cost | Monthly Cost (30d) | Annual Cost  |
|--------:|---------------:|-------------:|-----------:|-------------------:|-------------:|
| 100     | 500            | $0.012       | $6.00      | $180               | $2,160       |
| 1,000   | 5,000          | $0.012       | $60.00     | $1,800             | $21,600      |
| 10,000  | 50,000         | $0.012       | $600.00    | $18,000            | $216,000     |
| 100,000 | 500,000        | $0.012       | $6,000.00  | $180,000           | $2,160,000   |

### With Cost Optimization (see Section 4)

Assuming a 40% cost reduction through caching, model routing, and prompt optimization:

| DAU     | Daily Requests | Optimized Cost/Req | Daily Cost | Monthly Cost (30d) | Annual Cost  |
|--------:|---------------:|-------------------:|-----------:|-------------------:|-------------:|
| 100     | 500            | $0.0072            | $3.60      | $108               | $1,296       |
| 1,000   | 5,000          | $0.0072            | $36.00     | $1,080             | $12,960      |
| 10,000  | 50,000         | $0.0072            | $360.00    | $10,800            | $129,600     |
| 100,000 | 500,000        | $0.0072            | $3,600.00  | $108,000           | $1,296,000   |

---

## 4. Cost Optimization Strategies

### 4.1 Response Caching for Frequent Queries

Portfolio data does not change on every request. Caching tool responses for short windows (30-60 seconds) eliminates redundant LLM calls for repeated questions.

- **Impact:** 15-25% of requests can be served from cache
- **Implementation:** Redis TTL-based cache on tool outputs, keyed by tool name + parameters
- **Estimated savings:** ~20% reduction in total API costs

### 4.2 Model Routing with GPT-4o-mini

Use GPT-4o-mini ($0.15/$0.60 per 1M tokens) as a lightweight classifier to route simple queries before invoking GPT-4o. Simple greetings, clarification questions, and out-of-scope rejections do not require the full model.

- **GPT-4o-mini cost per classification:** ~$0.0001 (negligible)
- **Estimated 20-30% of queries** can be fully handled by GPT-4o-mini
- **Savings on routed queries:** ~95% per query (mini vs full model)
- **Net estimated savings:** ~15% reduction in total API costs

### 4.3 Prompt Optimization

The current system prompt (~400 tokens) plus tool schemas (~800 tokens) are sent with every request. Reducing prompt length and using more concise tool descriptions directly cuts input token costs.

- **Target:** Reduce system prompt + schemas from ~1,200 tokens to ~800 tokens (33% reduction)
- **Estimated savings:** ~5% reduction in total API costs

### 4.4 Market Data Caching

Symbol lookups and asset profiles rarely change. Caching market data responses for 5-15 minutes avoids redundant Ghostfolio API calls and the associated LLM processing of identical data.

- **Implementation:** Cache `market_data` and `benchmark_comparison` tool outputs in Redis
- **Estimated savings:** ~5% reduction (applies only to market data queries)

### 4.5 Per-User Rate Limiting

Prevent abuse and control runaway costs with per-user rate limits.

- **Recommended limits:** 50 queries/user/day for free tier, 200 for premium
- **Implementation:** Token bucket algorithm in Redis, checked before agent invocation
- **Cost impact:** Prevents worst-case cost scenarios; does not reduce average costs

### Combined Optimization Summary

| Strategy               | Estimated Savings |
|------------------------|------------------:|
| Response caching       | ~20%              |
| GPT-4o-mini routing    | ~15%              |
| Prompt optimization    | ~5%               |
| Market data caching    | ~5%               |
| **Total (compounded)** | **~40%**          |

---

## 5. Infrastructure Costs

### Railway Hosting

AgentForge runs four services on Railway: Ghostfolio (NestJS), PostgreSQL, Redis, and the Agent API (FastAPI).

| Service          | Description                       | Hobby Plan   | Pro Plan     |
|------------------|-----------------------------------|-------------:|-------------:|
| Ghostfolio       | NestJS backend + Angular frontend | ~$5/mo       | ~$10-20/mo   |
| PostgreSQL       | Database (Prisma ORM)             | ~$5/mo       | ~$10-20/mo   |
| Redis            | Cache + memory store              | ~$2/mo       | ~$5-10/mo    |
| Agent API        | FastAPI + LangChain agent         | ~$5/mo       | ~$10-20/mo   |
| **Total**        |                                   | **~$17/mo**  | **~$35-70/mo** |

Railway Hobby plan: $5/month base with usage-based pricing. Pro plan: $20/month base with higher resource limits and priority support.

### Scaling Infrastructure by DAU

| DAU     | Railway Tier | Estimated Infra Cost/mo | AI Cost/mo | Total Cost/mo |
|--------:|--------------|------------------------:|-----------:|--------------:|
| 100     | Hobby        | $17                     | $180       | $197          |
| 1,000   | Pro          | $50                     | $1,800     | $1,850        |
| 10,000  | Pro (scaled) | $150                    | $18,000    | $18,150       |
| 100,000 | Dedicated    | $500+                   | $180,000   | $180,500+     |

At all scales, AI API costs dominate infrastructure costs by an order of magnitude.

### LangSmith Observability

| Plan       | Traces/mo   | Cost/mo |
|------------|------------:|--------:|
| Free       | 5,000       | $0      |
| Plus       | 50,000      | $39     |
| Enterprise | Unlimited   | Custom  |

For the 100-DAU tier (~15,000 traces/month), the Plus plan is sufficient. At 1,000+ DAU, sampling traces (e.g., 10% of requests) keeps costs on the Plus plan while maintaining observability.

---

## 6. Summary

| Category                  | 100 DAU/mo | 1,000 DAU/mo | 10,000 DAU/mo |
|---------------------------|------------|--------------|---------------|
| AI API (GPT-4o)           | $180       | $1,800       | $18,000       |
| AI API (with optimization)| $108       | $1,080       | $10,800       |
| Infrastructure (Railway)  | $17        | $50          | $150          |
| Observability (LangSmith) | $0         | $39          | $39           |
| **Total (unoptimized)**   | **$197**   | **$1,889**   | **$18,189**   |
| **Total (optimized)**     | **$125**   | **$1,169**   | **$10,989**   |

### Key Takeaways

- Development costs are minimal (~$10-20 total) thanks to GPT-4o's competitive pricing.
- Per-request costs average ~1.2 cents, making the agent economically viable for small-to-medium user bases.
- AI API costs account for 90%+ of total costs at every scale; infrastructure is a rounding error by comparison.
- A 40% cost reduction is achievable through caching, model routing, and prompt optimization.
- At 10,000+ DAU, further cost reduction strategies (batching, fine-tuning a smaller model, or migrating to open-source LLMs) should be evaluated.

---

*Pricing data: OpenAI GPT-4o rates as of January 2025. Railway and LangSmith pricing as of early 2025. All projections assume 5 queries per user per day with a 70/30 single-tool/multi-tool split.*
