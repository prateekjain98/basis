# Architecture

This is a work trial for Meraki Labs. The brief: build a conversational agent with ≥2 tools and session memory, reliability over complexity.

## Why I picked this stack

### Supabase for the database

I started with raw PostgreSQL + SQLAlchemy. Wrote models, migrations, the whole thing. Then realized I was spending more time on schema versioning and connection pooling than on the actual agent. Deleted `db/models.py`, `db/base.py`, `db/session.py` — all gone.

Supabase gives me a Postgres instance with a REST API auto-generated on top. I don't write migrations; I just `CREATE TABLE` once and use the client. For a demo project this is the right tradeoff. The Python client (`supabase-py`) is sync, so the agent wraps calls in `asyncio.to_thread()`. Not elegant, but it works.

**The real downside:** The free tier pauses after 7 days of inactivity. For a portfolio project I don't care. For production I'd upgrade to Pro or self-host Postgres.

### Qdrant for vectors

I considered pgvector because I already had Postgres. But pgvector shares RAM with OLTP queries and degrades on filtered search. Qdrant is a single Docker container, filterable HNSW out of the box, and the Rust implementation is fast.

Each session gets its own collection (`session_<uuid>`). This is wasteful — a production setup would use one collection with `session_id` in the payload and filter on it. I went with per-session collections because it's simpler to reason about and easier to delete when a session ends.

### LlamaParse for PDFs

I tried PyMuPDF first. It returned scrambled text on multi-column financial reports — table rows got interleaved with footnotes. LlamaParse is the only tool I've found that consistently preserves table structure and converts charts to markdown. It's not free (1,000 pages/day on the free tier) but for a demo that's plenty.

Without a LlamaParse key, the parser returns `None` and the agent falls back to web snippets. The pipeline doesn't crash.

### No LangChain / LangGraph

I looked at LangGraph for the multi-step pipeline. It would give me a nice DAG visualization and built-in retry logic. But for a linear pipeline (search → fetch → parse → index → retrieve → score), LangGraph adds 200 lines of boilerplate and obscures what's happening. My `agent.py` is ~200 lines of plain Python. I can read it top-to-bottom and know exactly what happens on each turn.

If I needed multi-agent collaboration (e.g., a research agent + a risk agent debating), LangGraph would make sense. For a single research pipeline, it's overkill.

### yfinance for financial data

Bloomberg requires a terminal license. Alpha Vantage rate-limits to 5 requests/minute on the free tier. Polygon.io is good but $199/month.

yfinance is free, no API key, and returns the metrics I need (P/E, margins, growth, debt). The tradeoff: it scrapes Yahoo Finance, which can block IPs after heavy use and sometimes returns stale data. I handle this by catching all exceptions and scoring with whatever data is available.

### Autonomous document discovery

The user does not upload PDFs. The agent searches the web, filters for real PDFs, downloads them, and parses. This is harder than manual upload because:
- Web search results are noisy
- PDFs might be paywalled or corrupted
- The corpus changes every day

But manual upload is a toy feature. Real analysts search for the latest report. I wanted the agent to mirror that workflow.

## Scoring rubric

Each stock gets a 0-100 score:

| Factor | Weight | Source |
|--------|--------|--------|
| Fundamentals | 30% | P/E, ROE, revenue growth, margins (yfinance) |
| Thematic Fit | 25% | LLM judgment from document context |
| Risk | 20% | Debt/equity, market cap, 52W range position |
| Momentum | 15% | Revenue growth trajectory |
| Liquidity | 10% | Market cap |

The weights are hard-coded. This makes the scoring explainable — you can verify that a high P/E correctly drags down the fundamentals score. A learned model would be more accurate but opaque.

## Deployment

- Frontend: Vercel (Next.js, edge CDN)
- Backend: Fly.io (container platform, free tier)
- Vector DB: Qdrant Cloud or self-hosted
- Relational DB: Supabase

At zero traffic: $0/month.
