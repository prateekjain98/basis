# work trial writeup

Built an agent that researches investment themes and returns scored stock recommendations. User types "AI infrastructure", agent finds real PDFs, reads them, returns a thesis with 3-5 stocks ranked 0-100.

## what it does

1. **Search** — 4 DDG queries to find ~30 PDF candidates
2. **Score** — URL heuristics rank by domain trust, `.pdf` extension, year in path
3. **Download** — top 15 candidates in parallel, 20s timeout per future
4. **Parse** — LlamaParse → markdown (tables preserved). No key = skip
5. **Index** — chunk + embed → Qdrant, one collection per session
6. **Retrieve** — top-8 passages for the query
7. **Synthesize** — LLM reads passages, returns JSON with stocks
8. **Score** — yfinance fundamentals + 5-factor rubric

Follow-ups skip steps 1-4. Reuses existing corpus, blends conversation history into retrieval.

## stack

FastAPI + Pydantic backend. Supabase for sessions/stocks/docs/messages. Qdrant for vectors. LlamaIndex + LlamaParse for PDFs. yfinance for financial data. Next.js + Vercel AI SDK frontend.

## what actually happened

**Day 1: frontend archaeology.** The starter template was the full Vercel AI Chatbot — AI Gateway, artifacts, auth, model selector, credit card alerts. Spent 4 hours stripping it. The proxy in `frontend/app/(chat)/api/chat/route.ts` is the only frontend code I wrote.

**Day 2: backend.** Started with SQLAlchemy + Alembic. Wrote models, migrations, connection pooling. Spent an hour fighting migration versions before deleting all of it. Switched to Supabase. The Python client is sync-only, so every DB call is wrapped in `asyncio.to_thread()`.

**Day 3: document discovery.** First `DocumentFetcher` ran one DDG query and downloaded the first 3 `.pdf` links. Most were HTML landing pages. Current version scores 30+ candidates, validates `Content-Type`, checks magic bytes, rejects <10KB files.

## things that broke

**Python 3.14 killed LlamaIndex.** `pip install llama-index` exploded with a C extension build failure. Downgraded to 3.13. Lost 20 minutes.

**DDG returned ChatGPT's homepage as a "PDF."** Old `duckduckgo-search` package is deprecated. Switched to `ddgs`. Still noisy — without Tavily, 30% of candidates are blog posts.

**ThreadPoolExecutor hung forever.** One URL accepted TCP, sent zero bytes. `future.result()` blocked. Added 20s timeout per future.

**GPT-4o-mini wraps JSON in markdown.** ~30% of runs. Current fix: `.removeprefix("```json")`. Hack.

**yfinance throttled after 20 tickers.** Scores return `None`. Catch exceptions, return partial data. No fallback source.

**Follow-ups had no memory.** Original `/chat` only used `messages[-1]`. Added `messages` table, blended last 4 messages into retrieval query. Still noisy.

## current state

- Document discovery: works
- Document parsing: works if LlamaParse key set
- Vector indexing: needs real OpenAI key (embeddings)
- Stock scoring: works, uses real yfinance data
- LLM synthesis: **blocked — needs real API key**
- Follow-ups: implemented, retrieval context is noisy
- Frontend: stripped template, only chat proxy works

## blockers

OpenAI API key in `.env` is dummy. Everything up to the LLM call runs. Then dies at `chat.completions.create()`. Free alternatives: OpenRouter (signup, free models), Together AI ($5 credit), Ollama locally.

## files

| file | what |
|------|------|
| `backend/src/agent.py` | whole pipeline, ~200 lines |
| `backend/src/tools/document_fetcher.py` | finds 30 PDFs, returns best 5 |
| `backend/src/tools/stock_scorer.py` | yfinance + rubric |
| `backend/schema.sql` | Supabase table definitions (use migrations instead) |
| `frontend/app/(chat)/api/chat/route.ts` | Vercel AI SDK → FastAPI proxy |

## run

```bash
cd backend && source .venv/bin/activate && uvicorn src.main:app --reload
cd frontend && npm run dev
```

Needs `OPENAI_API_KEY`. `LLAMA_CLOUD_API_KEY` and `TAVILY_API_KEY` optional.
