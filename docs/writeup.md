# Work Trial Write-Up: Basis

## What I Built

Basis is an autonomous investment research agent. You type a theme like "AI infrastructure" or "DeepSeek disruption" and it goes and finds real PDFs, reads them, and tells you which stocks to buy and why.

The flow is:
1. Search the web for recent investment reports (not just any web page — actual PDFs)
2. Download the best ones using a scoring system that filters out blogspam and landing pages
3. Parse them with LlamaParse to preserve tables and reading order
4. Chunk and index in Qdrant for semantic search
5. Retrieve relevant passages and synthesize a thesis via LLM
6. Score 3-5 recommended stocks on a 5-factor rubric using real yfinance data
7. Persist everything to Supabase so you can come back later and ask follow-up questions

Each thesis is a persistent chat session. Follow-up questions use the existing document corpus — the agent doesn't re-search the web, it just retrieves new passages relevant to your follow-up and adjusts the thesis.

## Decisions I Made

**Supabase over raw Postgres:** I started with SQLAlchemy + Alembic migrations. Spent an hour on schema versioning before realizing I was solving a problem I didn't have. Deleted all the ORM code and switched to Supabase. The Python client is sync, so I wrap DB calls in `asyncio.to_thread()`. It's not pretty but it means I never think about migrations.

**Qdrant over pgvector:** pgvector works but filtered search gets slow past ~1M vectors. Qdrant is a single Docker container and HNSW is its default. I also liked that I could delete a whole session's vectors by dropping a collection.

**LlamaParse over PyMuPDF:** I tried PyMuPDF first on a multi-column Goldman report. The text came out as a scrambled mix of left-column and right-column sentences. LlamaParse preserved the tables as markdown. It's the only parser I've found that handles financial PDFs well.

**Plain Python over LangGraph:** LangGraph would give me a nice DAG and built-in retries. But my pipeline is a straight line: search → fetch → parse → index → retrieve → score. LangGraph would add 200 lines of abstraction for no benefit. If I ever add a second agent (e.g., a risk specialist that debates the main analyst), then LangGraph becomes worth it.

**Autonomous discovery over manual upload:** Manual upload is easy to build but useless in practice. Real analysts don't upload PDFs — they Google for the latest report. The hard part is filtering the search results. My first version found 3 PDFs and hoped for the best. The current version searches 4 different queries, scores 30+ candidates on domain authority and URL signals, and validates downloads before parsing.

## What Actually Broke

**1. The Vercel AI Chatbot template was a mess.**
The initial frontend was the full Vercel template with AI Gateway, artifacts, auth pages, and a database dependency. It took me longer to strip it down to a simple proxy than it would have taken to build a chat UI from scratch. I kept the Vercel AI SDK for the streaming plumbing but removed everything else.

**2. Python 3.14 broke LlamaIndex.**
I created the venv with Python 3.14 (the latest on my machine). `pip install llama-index` failed with a C extension compilation error. Downgraded to 3.13 and everything worked. This wasted ~20 minutes.

**3. DuckDuckGo search returned garbage.**
My first web search implementation used `duckduckgo-search` (the old package name). It returned OpenAI's homepage and ChatGPT's login page as "search results" for "AI infrastructure investment report pdf." I switched to `ddgs` (the renamed package) and the results improved, but it's still hit-or-miss. Without a Tavily key, ~30% of "PDF" URLs are actually HTML landing pages.

**4. Parallel downloads hung forever.**
I used `ThreadPoolExecutor` to download 15 candidate PDFs in parallel. One URL (a broken CDN) accepted the connection and then sent nothing. `future.result()` waited forever and the whole agent stalled. I added a 20-second timeout per future and a 120-second timeout on `as_completed()`.

**5. GPT-4o-mini wrapped JSON in markdown fences.**
About 1 in 3 test runs, the LLM returned:
```json
{"theme": "...", "stocks": [...]}
```
instead of raw JSON. `json.loads()` threw `JSONDecodeError`. I added stripping logic but I should probably switch to OpenAI's structured output API (`response_format={"type": "json_object"}`) for reliability.

**6. yfinance rate-limited me.**
After scoring ~20 stocks in rapid succession during testing, yfinance started returning 403s. I added exception handling so missing data doesn't crash the pipeline, but the scores become less useful when fundamentals are blank.

**7. Follow-ups were completely broken.**
The original `/chat` endpoint received the full `messages` array from the frontend but literally discarded everything except `messages[-1]`. So "what if GPU demand crashes?" was treated as a brand-new query with no memory. I added a `messages` table, loaded history on follow-up turns, and blended conversation context into the retrieval query.

## What I Would Do Next

1. **Structured outputs:** Use OpenAI's `response_format={"type": "json_object"}` instead of regex-stripping markdown fences. More reliable, less hacky.

2. **Ticker validation:** Before calling yfinance, validate the ticker against a real database (e.g., NASDAQ's API). The LLM sometimes invents tickers that don't exist.

3. **Citation layer:** Every stock claim should cite the specific document passage it came from. LlamaParse preserves page numbers in the metadata; I should surface them in the UI.

4. **Single collection with filters:** Per-session Qdrant collections are wasteful. A single `document_chunks` collection with `session_id` in the payload would scale better.

5. **Better search:** Tavily is much better than DDG for finding institutional PDFs. Without a Tavily key the agent struggles to find high-quality sources.

## How to Run

```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload
```

Frontend:
```bash
cd frontend
npm run dev
```

Requires `OPENAI_API_KEY` in `backend/.env`. `LLAMA_CLOUD_API_KEY` and `TAVILY_API_KEY` are optional but improve quality significantly.

## Deliverables

| Deliverable | Status | Location |
|-------------|--------|----------|
| Working agent with ≥2 tools + session memory | Done | `backend/src/agent.py` |
| Architecture decision doc | Done | `docs/architecture.md` |
| Eval suite | Done | `eval/` |
| Failure write-up | Done | `docs/failure_modes.md` |
| Written doc | Done | `docs/writeup.md` |
