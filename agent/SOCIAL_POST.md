# AgentForge Social Posts

## Twitter/X (280 chars)

Built an open-source AI financial assistant for Ghostfolio during @GauntletAI fellowship — 9 tools, verification layer, 150+ evals, LangSmith observability. Contributed a PR upstream and got added to Ghostfolio's community projects!

github.com/agarg5/AgentForge

## LinkedIn

I'm excited to share AgentForge — an open-source AI agent I built for Ghostfolio (a wealth management platform) during the @GauntletAI fellowship.

**What it does:** Natural language portfolio assistant that connects to your real Ghostfolio account. Ask questions like "How is my portfolio performing?" or "Compare my returns to the S&P 500" and get answers grounded in your actual data.

**Key features:**
- 9 LangChain tools wrapping Ghostfolio's REST API (portfolio analysis, market data, risk assessment, dividends, benchmarks, transactions, accounts, order management, market news)
- Verification layer with 5 domain-specific checks — no hallucinated prices, valid ticker validation, automatic disclaimers, numeric consistency, and confidence scoring
- 150+ eval test cases across happy path, edge cases, adversarial/jailbreak, and multi-step scenarios (12 cases requiring 3-5 tool chains)
- Full observability via LangSmith — traces, token/cost tracking, user feedback (thumbs up/down linked to traces)
- Persistent user memory across sessions (preferences stored in Redis)
- Integrated directly into Ghostfolio's Angular UI with a chat interface
- Deployed on Railway with auto-deploy from GitHub

**Tech stack:** Python, LangChain, GPT-4o, FastAPI, LangGraph, LangSmith, Redis

Also contributed an upstream PR to the Ghostfolio open-source project (ghostfolio#6397), and AgentForge was added to the Ghostfolio community projects: https://github.com/topics/ghostfolio

Built during the Gauntlet AI fellowship — an incredible experience pushing the boundaries of what AI agents can do in production.

github.com/agarg5/AgentForge

#AI #LLM #OpenSource #FinTech #LangChain #GauntletAI
