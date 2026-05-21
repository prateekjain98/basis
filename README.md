<div align="center">

# Basis

**A conversational agent for autonomous thematic investment research.**

State a thesis → discover documents → synthesize a thesis → score trades → track with session memory.

[![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

<p align="center">
  <a href="https://meraki.prateekjain.io">Live Demo</a> ·
  <a href="./docs/architecture.md">Architecture</a> ·
  <a href="./docs/evaluation.md">Eval Suite</a> ·
  <a href="./docs/failure_modes.md">Failure Modes</a>
</p>

---

<details open>
<summary><b>📕 Table of Contents</b></summary>

- [What is Basis?](#-what-is-basis)
- [How it works](#-how-it-works)
- [Quickstart](#-quickstart)
- [Project Structure](#-project-structure)
- [Tools](#-tools)
- [Session Memory](#-session-memory)
- [Eval Suite](#-eval-suite)
- [Deployment](#-deployment)
- [Environment](#-environment)
- [Current State](#-current-state)
- [License](#-license)

</details>

## 💡 What is Basis?

Basis is a conversational agent built for a multi-step task: **thematic investment research**. You state an investment thesis — "AI infrastructure for the next decade" — and the agent:

1. **Discovers** real research documents (PDF reports, SEC filings, whitepapers) from the open web
2. **Parses** them into structured text with preserved tables
3. **Indexes** passages into a per-session vector store
4. **Synthesizes** a structured investment thesis via LLM
5. **Scores** every recommended stock on a 5-factor rubric using live market data
6. **Persists** the full thesis so follow-up questions reuse the document corpus

The agent uses **multiple tools** (document discovery, financial data, vector search) and maintains **session memory** across turns.

> This project was built as a work trial assignment: *"Build a conversational agent for a multi-step task of your choice. At least 2 tools and session memory. Reliability over complexity."*

## 🔎 How it works

```
User Query
    │
    ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Document       │───▶│  Vector Store   │───▶│  LLM Synthesis  │
│  Discovery      │    │  (Qdrant)       │    │  (OpenAI)       │
│  (Web Search +  │    │                 │    │                 │
│   PDF Fetch)    │    │  Per-session    │    │  JSON thesis    │
└─────────────────┘    │  collections    │    │  output         │
                       └─────────────────┘    └─────────────────┘
                              │                        │
                              ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Session Memory │    │  Stock Scorer   │
                       │  (Supabase)     │    │  (yfinance)     │
                       │                 │    │                 │
                       │  Documents,     │    │  5-factor rubric│
                       │  messages,      │    │  live data      │
                       │  trades         │    │                 │
                       └─────────────────┘    └─────────────────┘
```

**Pipeline (first turn):**

| Step | Tool | What it does |
|------|------|--------------|
| Discover | `DocumentFetcher` + `WebSearchTool` | 4 search strategies, 30 candidates scored on domain authority |
| Download | `DocumentFetcher` | Parallel fetch, magic-byte validation, 20s timeout |
| Parse | `DocumentParser` | LlamaParse primary, PyMuPDF fallback |
| Index | `SessionVectorStore` | Chunk + embed → Qdrant per-session collection |
| Retrieve | `SessionVectorStore` | Top-8 passages blended with conversation context |
| Synthesize | `_llm_chat()` | JSON output: theme, conviction, summary, stock list |
| Score | `StockScorer` | yfinance + 5-factor rubric |
| Track | Supabase client | Full trade journal with rationale, entry, target |

**Pipeline (follow-up):**

| Step | What changes |
|------|--------------|
| Discover | **Skipped** — reuses existing corpus |
| Retrieve | Blends last 4 messages into retrieval query |
| Synthesize | Includes message history in LLM context |

## 🚀 Quickstart

### Prerequisites

- Python 3.13
- Node.js 20+
- Docker (for local Qdrant)
- OpenAI API key

### Backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Add OPENAI_API_KEY to .env
```

### Frontend

```bash
cd frontend
npm install
```

### Run

```bash
# Start Qdrant
docker compose up -d qdrant

# Terminal 1 — Backend
cd backend && uvicorn src.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open http://localhost:3000.

### API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "AI infrastructure buildout"}]}'
```

## 📁 Project Structure

```
backend/
  src/
    agent.py              # Orchestrator: discover → parse → index → retrieve → score
    main.py               # FastAPI: /chat, /sessions, /health
    models/schemas.py     # Pydantic models for financial metrics
    tools/
      document_fetcher.py # Multi-strategy search + scoring
      document_parser.py  # LlamaParse + PyMuPDF fallback
      vector_store.py     # Qdrant session manager
      stock_scorer.py     # yfinance + rubric
      web_search.py       # Tavily / DuckDuckGo
frontend/
  app/(chat)/api/chat/route.ts  # Vercel AI SDK → FastAPI proxy
  components/chat/              # Chat UI shell
  hooks/use-active-chat.tsx     # Chat state management
eval/
  metrics.py            # Automated scoring logic
  run_eval.py           # Eval runner
  test_cases.json       # 8 test cases
tests/
  test_agent.py         # Unit tests for tool reliability
```

## 🛠️ Tools

### Document Discovery (`DocumentFetcher`)

- **4 search strategies**: `filetype:pdf`, equity research, sector outlook, analysis report
- **URL scoring**: domain authority (SEC = 3.0, Medium = 0.5), `.pdf` extension, year in path
- **Parallel download**: 15 candidates, 20s timeout per future
- **Validation**: Content-Type check, magic bytes (`%PDF`), size bounds (10KB–100MB)

### Stock Scorer (`StockScorer`)

- **Data source**: yfinance (free, no API key)
- **5-factor rubric**:

| Factor | Weight | Source |
|--------|--------|--------|
| Fundamentals | 30% | P/E, ROE, revenue growth, margins |
| Thematic fit | 25% | LLM judgment from document context |
| Risk | 20% | Debt/equity, market cap, 52W range |
| Momentum | 15% | Revenue growth trajectory |
| Liquidity | 10% | Market cap |

- **Graceful degradation**: Missing fields default to neutral 50/100. Fake tickers return `None` fields without crashing.

### Vector Store (`SessionVectorStore`)

- **Backend**: Qdrant (local Docker or Qdrant Cloud)
- **Per-session collections**: One collection per `session_id`
- **Fallback**: In-memory keyword search when Qdrant unavailable

### Web Search (`WebSearchTool`)

- **Primary**: Tavily API (curated results)
- **Fallback**: DuckDuckGo (`ddgs`)

## 🧠 Session Memory

Session memory is dual-layer:

1. **Document corpus persistence**: Every document found in the first turn is saved to Supabase (`documents` table) and indexed in Qdrant. Follow-ups check if documents exist; if yes, they skip search/fetch/parse/index entirely.

2. **Message history blending**: Follow-ups concatenate the last 4 messages into the retrieval query, giving the vector search conversation context without a separate memory store.

```python
# From agent.py — follow-up retrieval
if is_followup and len(history) >= 2:
    recent = history[-4:]
    retrieval_query = " | ".join(
        f"{m['role']}: {m['content'][:100]}" for m in recent
    )
    retrieval_query += f" | now: {query}"
```

## 📊 Eval Suite

`eval/run_eval.py` runs 8 test cases against the live backend:

| ID | Test | What it validates |
|----|------|-------------------|
| tc-01 | Simple ticker query | Basic tool use + financial data |
| tc-02 | Thematic without ticker | Document discovery path |
| tc-03 | Follow-up in session | Session memory recall |
| tc-04 | Ambiguous prompt | Graceful degradation |
| tc-05 | Bad ticker | Tool failure handling |
| tc-06 | International market | Non-US ticker support |
| tc-07 | Multi-turn memory | Comparison across history |
| tc-08 | No search results | Empty corpus handling |

**Metrics:**
- **Task completion**: Thesis structure checks (has_theme, has_rationale, has_risks, has_conviction)
- **Hallucination detection**: Extract numbers from thesis, verify against raw tool output
- **Graceful failure**: Acknowledges ambiguity, acknowledges data gaps, still generates thesis

Run:
```bash
cd eval && python run_eval.py
```

See [`docs/evaluation.md`](./docs/evaluation.md) for full details.

## 🚀 Deployment

**Backend → Google Cloud Run**

```bash
cd backend
gcloud builds submit --tag gcr.io/PROJECT/basis-backend
gcloud run deploy basis-backend --image gcr.io/PROJECT/basis-backend --allow-unauthenticated
```

**Frontend → Vercel**

```bash
cd frontend
vercel --prod
```

## 🔧 Environment

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | LLM synthesis + embeddings |
| `QDRANT_URL` | Yes | Vector store |
| `QDRANT_API_KEY` | For Cloud | Qdrant Cloud auth |
| `SUPABASE_URL` | Yes | Session persistence |
| `SUPABASE_KEY` | Yes | Supabase service role key |
| `TAVILY_API_KEY` | Optional | Premium search (falls back to DDG) |
| `LLAMA_CLOUD_API_KEY` | Optional | PDF parsing (falls back to PyMuPDF) |

## 📄 Deliverables

This repository contains all assignment deliverables:

| Deliverable | Location |
|---|---|
| Working agent with tool use and session memory | [`backend/src/agent.py`](./backend/src/agent.py) |
| Architecture decision doc | [`docs/architecture.md`](./docs/architecture.md) |
| Eval suite | [`eval/`](./eval/) + [`docs/evaluation.md`](./docs/evaluation.md) |
| Write-up of where the agent breaks | [`docs/failure_modes.md`](./docs/failure_modes.md) |

## License

MIT
