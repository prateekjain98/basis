# basis

Agent that searches the web for investment reports, reads them, and tells you what stocks to buy.

## install

```bash
git clone https://github.com/prateekjain98/basis.git
cd basis

# backend
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# frontend
cd ../frontend
npm install
```

Python 3.14 will not work. LlamaIndex C extensions fail on 3.14.

## configure

```bash
cp backend/.env.example backend/.env
```

Required:

| var | for |
|-----|-----|
| `OPENAI_API_KEY` | LLM + embeddings |
| `SUPABASE_URL` | sessions, stocks, messages |
| `SUPABASE_KEY` | sessions, stocks, messages |

Optional:

| var | for | fallback if missing |
|-----|-----|---------------------|
| `LLAMA_CLOUD_API_KEY` | PDF parsing | web snippets only |
| `TAVILY_API_KEY` | web search | DuckDuckGo (worse results) |
| `OPENAI_BASE_URL` | Groq, Together, etc | OpenAI default |

No OpenAI key? Use OpenRouter (free models):

```
OPENAI_API_KEY=sk-or-v1-...
OPENAI_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.1-70b-instruct
```

## run

```bash
# 1. start qdrant
docker compose up -d qdrant

# 2. start backend (port 8000)
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload

# 3. start frontend (port 3000)
cd frontend
npm run dev
```

Then open http://localhost:3000.

## how it works

`POST /chat` accepts `{messages, session_id}` and streams back a thesis.

First turn:
```
search web → find 30 PDF candidates → score URLs → download top 15
→ parse with LlamaParse → chunk → index in Qdrant
→ retrieve top-8 passages → LLM synthesizes thesis
→ score stocks with yfinance → save to Supabase
```

Follow-up:
```
reuse existing index → blend conversation history into retrieval query
→ LLM adjusts thesis → save
```

## api

| endpoint | method | what |
|----------|--------|------|
| `/chat` | POST | stream thesis. body: `{messages, session_id}` |
| `/sessions` | GET | list all sessions |
| `/sessions/{id}` | GET | session with stocks, docs, messages |
| `/sessions/{id}` | DELETE | drop session + vectors |
| `/health` | GET | ok |

## project layout

```
backend/src/
  agent.py              # pipeline: search → fetch → parse → index → retrieve → score
  main.py               # FastAPI endpoints
  tools/
    document_fetcher.py # find 30 PDFs, return best 5
    document_parser.py  # LlamaParse wrapper
    vector_store.py     # Qdrant session manager
    stock_scorer.py     # yfinance + 5-factor rubric
    web_search.py       # Tavily / DDG
frontend/app/(chat)/api/chat/route.ts   # proxy to backend
```

## test

```bash
cd backend
source .venv/bin/activate
pytest ../tests/test_agent.py -v
```

The vector store test is skipped without a real OpenAI key (embeddings).

## known issues

- **Needs real OpenAI key.** Dummy key in `.env` is a placeholder. LLM synthesis and embeddings both fail without it.
- **yfinance rate-limits.** ~20 rapid ticker lookups and Yahoo starts returning 403s. Scores degrade to neutral 50s.
- **DDG search is noisy.** ~30% of "PDF" links are HTML landing pages. The fetcher filters most out.
- **Per-session Qdrant collections are wasteful.** 50 sessions = 50 collections. No auto-cleanup.
- **Frontend is stripped template cruft.** Still has artifact code and AI Gateway references. Only the chat proxy works.

## deploy

Backend + Qdrant → Fly.io:
```bash
fly launch --dockerfile backend/Dockerfile
```

Frontend → Vercel:
```bash
vercel --prod
```

Costs $0 at rest on free tiers.
