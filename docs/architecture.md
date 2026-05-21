# architecture

Not an ADR. Just notes on why things are the way they are.

## supabase

I started with SQLAlchemy + Alembic. Wrote models, migrations, connection pooling. Realized I was spending more time on schema versioning than the agent. Deleted `db/models.py`, `db/base.py`, `db/session.py`.

Supabase gives you a Postgres instance with a REST API auto-generated on top. The Python client (`supabase-py`) is sync-only, so the agent wraps calls in `asyncio.to_thread()`. Ugly but it works.

The schema is managed via Supabase CLI migrations (`supabase/migrations/`). I used to have a hand-written `schema.sql` — that was wrong. Use `supabase migration new` and `supabase db push`.

## qdrant

pgvector shares RAM with OLTP queries and filtered search gets slow past ~1M vectors. Qdrant is a single Docker container and HNSW is the default.

Each session gets its own collection (`session_<uuid>`). This is wasteful — a production setup would use one collection with `session_id` in the payload. I went with per-session because deleting a session's vectors is one `DELETE collection` call. Laziness.

## llama-parse

PyMuPDF returns scrambled text on multi-column financial reports — table rows get interleaved with footnotes. LlamaParse is the only parser I've found that consistently preserves table structure and converts charts to markdown.

Without a LlamaParse key, `DocumentParser.parse()` returns `None` and the agent falls back to web snippets. The pipeline doesn't crash.

## no langchain

LangGraph would give me a DAG visualization and built-in retries. But the pipeline is a straight line:

```
search → fetch → parse → index → retrieve → score
```

LangGraph adds ~200 lines of boilerplate for no benefit. `agent.py` is ~200 lines of plain Python. I can read it top-to-bottom and know exactly what happens.

If I ever add a second agent (e.g., a risk analyst that debates the main researcher), LangGraph becomes worth it.

## yfinance

Bloomberg needs a terminal license. Alpha Vantage rate-limits to 5 req/min free. Polygon.io is $199/mo.

yfinance is free, no API key, returns P/E, margins, growth, debt. The tradeoff: it scrapes Yahoo Finance, which blocks IPs after heavy use. The scorer catches all exceptions and returns partial data. Missing fields default to neutral 50.

## scoring rubric

Hard-coded weights. Explorable, not learned.

| factor | weight | source |
|--------|--------|--------|
| fundamentals | 30% | P/E, ROE, revenue growth, margins |
| thematic fit | 25% | LLM judgment from document context |
| risk | 20% | debt/equity, market cap, 52W range |
| momentum | 15% | revenue growth trajectory |
| liquidity | 10% | market cap |

## document discovery

The user does not upload PDFs. The agent searches, filters, downloads, parses. Harder than manual upload because:
- Web search results are noisy
- PDFs might be paywalled or corrupted  
- Corpus changes every day

My first version ran one DDG query and downloaded the first 3 `.pdf` links. Most were HTML landing pages. The current version:
- 4 search queries (`filetype:pdf`, `"equity research"`, etc.)
- Score 30+ candidates on domain authority (sec.gov = 3.0, medium.com = 0.5)
- Validate `Content-Type`, magic bytes (`%PDF`), size (10KB min)
- Download top 15 in parallel with 20s timeout
- Return best 5

## deployment

- Frontend: Vercel
- Backend: Fly.io
- Vector DB: Qdrant Cloud or self-hosted
- Relational DB: Supabase

$0/month at rest.
