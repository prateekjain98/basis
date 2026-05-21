# basis

Autonomous investment research agent. Type a theme, it finds PDF reports, reads them, returns scored stock theses.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"invest in AI infrastructure"}]}'
```

Output (streamed):
```
**Thesis ID:** `a1b2c3d4`

**Searching** for reports...
- Found: AI Infrastructure Investment WHITEPAPER - meketa.com
- Found: [PDF] building the backbone of AI. - Brookfield

**Parsing**...
- AI Infrastructure WHITEPAPER: 45231 chars
- Brookfield: 12894 chars

**Indexing**...
- 89 chunks indexed

**Retrieving** relevant passages...
1. Data center capex expected to reach $500B by 2027...
2. Power constraints are the primary bottleneck for AI infrastructure expansion...
3. NVIDIA maintains 80%+ market share in AI accelerators...

**Analyzing**...
**Scoring** NVDA...
**Scoring** VST...
**Scoring** DLR...

## AI Infrastructure Buildout

**Conviction:** High

### Executive Summary
Data center capex is accelerating. Power and cooling constraints create moats for existing players. NVIDIA, Vistra, and Digital Realty are best positioned.

### Recommended Positions
- **NVDA** (NVIDIA Corp) — Score: 87/100
  - Entry: $128.50
  - F:92 T:95 R:68 M:88 L:90
  - Dominant AI accelerator share, capex confirmation from hyperscalers

- **VST** (Vistra Corp) — Score: 74/100
  - Entry: $97.20
  - F:72 T:88 R:55 M:65 L:70
  - Power bottleneck = pricing power for nuclear/gas assets

- **DLR** (Digital Realty Trust) — Score: 71/100
  - Entry: $145.30
  - F:68 T:82 R:60 M:58 L:85
  - Data center REIT benefiting from AI demand pull-through
```

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

Python 3.14 won't work. LlamaIndex C extensions fail to compile.

## configure

```bash
cp backend/.env.example backend/.env
```

| var | what it's for |
|-----|---------------|
| `OPENAI_API_KEY` | LLM synthesis + embeddings (required) |
| `SUPABASE_URL` | database (required) |
| `SUPABASE_KEY` | database (required) |
| `LLAMA_CLOUD_API_KEY` | PDF parsing (optional, falls back to web snippets) |
| `TAVILY_API_KEY` | better web search (optional, DDG fallback) |

No OpenAI key? Use [OpenRouter](https://openrouter.ai) — free models, zero code changes:

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

Open http://localhost:3000. Chat interface proxies to the FastAPI backend.

## api

`POST /chat` — stream a thesis. Body: `{messages, session_id}`.

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role":"user","content":"invest in AI infrastructure"}],
    "session_id": null
  }'
```

`GET /sessions` — list all thesis sessions.

`GET /sessions/{id}` — session with stocks, documents, and message history.

`DELETE /sessions/{id}` — delete session and drop its vector collection.

## how it works

`backend/src/agent.py`. ~200 lines.

First turn:
1. Search web — 4 DDG queries, score 30 candidates, download top 15
2. Parse — LlamaParse to markdown. No key = skip
3. Index — chunk + embed → Qdrant (one collection per session)
4. Retrieve — top-8 passages
5. Synthesize — LLM reads passages, returns JSON
6. Score — yfinance fundamentals + 5-factor rubric
7. Persist — Supabase

Follow-up — skips search/parse/index. Reuses corpus, blends conversation history into retrieval.

## tests

```bash
cd backend
source .venv/bin/activate
pytest ../tests/test_agent.py -v
```

Covers web search, document fetching, stock scoring. Vector store test skipped without real OpenAI key (embeddings need it).

## deploy

Backend + Qdrant → Fly.io:
```bash
fly launch --dockerfile backend/Dockerfile
```

Frontend → Vercel:
```bash
vercel --prod
```

Stack costs $0 at rest on free tiers.

## project layout

```
backend/src/
  agent.py              # pipeline
  main.py               # FastAPI endpoints
  tools/
    document_fetcher.py # find 30 PDFs, return best 5
    document_parser.py  # LlamaParse wrapper
    vector_store.py     # Qdrant session manager
    stock_scorer.py     # yfinance + rubric
    web_search.py       # Tavily / DDG
frontend/app/(chat)/api/chat/route.ts   # proxy to backend
```

## license

MIT
