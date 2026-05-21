# Basis

> An autonomous research agent that finds, reads, and reasons over investment documents to generate scored stock theses.

Basis is a document-driven conversational agent. You describe an investment theme — "AI infrastructure," "DeepSeek disruption," "India renewables" — and the agent autonomously searches for relevant reports and filings, parses them with LlamaParse, indexes them in Qdrant, and synthesizes a structured thesis with scored stock recommendations. Each thesis is a persistent chat session with one-to-many stock picks.

Built as a **reliability-first** system: explicit state machine, structured outputs on every LLM call, graceful degradation when data sources fail, and real financial data grounding every score.

---

## Quickstart

```bash
git clone https://github.com/prateekjain98/basis.git
cd basis

# 1. Configure backend
cp backend/.env.example backend/.env
# Add OPENAI_API_KEY, LLAMA_CLOUD_API_KEY, SUPABASE_URL, SUPABASE_KEY

# 2. Start Qdrant locally
docker compose up -d qdrant

# 3. Run backend
cd backend
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Run frontend (new terminal)
cd frontend
npm run dev

# 5. Open http://localhost:3000
```

---

## What It Does

```
User: "Investment thesis on AI infrastructure buildout"

  Step 1: SEARCH    → Find recent PDF reports, 10-Ks, analyst notes
  Step 2: FETCH     → Download top-3 relevant documents
  Step 3: PARSE     → LlamaParse extracts tables, text, charts
  Step 4: INDEX     → Chunk and embed into Qdrant (session-scoped)
  Step 5: RETRIEVE  → Pull relevant passages for synthesis
  Step 6: SYNTHESIZE→ LLM proposes 3-5 stocks with rationale
  Step 7: SCORE     → Real financials + risk + momentum + liquidity
  Step 8: PERSIST   → Thesis + stocks saved to Supabase

Output:
  ┌─────────────────────────────────────────────┐
  │  THEME: AI Infrastructure Buildout          │
  │  CONVICTION: HIGH                           │
  │                                             │
  │  NVDA — Score: 87/100                       │
  │    Entry: $128.50 | Fundamentals: 92        │
  │    Thematic Fit: 95 | Risk: 68 | Momentum: 88│
  │    Rationale: Capex confirmation, 75% to AI │
  │                                             │
  │  VST — Score: 74/100                        │
  │    Entry: $97.20  | Risk: 55 (rate exposure)│
  │    Rationale: Power bottleneck = pricing pwr│
  └─────────────────────────────────────────────┘
```

---

## Architecture

```
┌──────────────┐     ┌──────────────────────┐     ┌─────────────┐
│   Next.js    │────▶│   FastAPI Backend    │────▶│   Qdrant    │
│  (Chat UI)   │◀────│  LlamaParse + Index  │◀────│ (Vector DB) │
│              │     │  Web Search + Fetch  │     └─────────────┘
│  useChat     │     │  OpenAI Synthesis    │
│  shadcn/ui   │     │  yfinance Scoring    │     ┌─────────────┐
└──────────────┘     └──────────────────────┘────▶│  Supabase   │
                                                  │  (Sessions, │
                                                  │   Stocks,   │
                                                  │   Docs)     │
                                                  └─────────────┘
```

| Component | Purpose | Tech |
|-----------|---------|------|
| **Frontend** | Chat interface, streaming display | Next.js 15 + Vercel AI SDK UI + shadcn/ui |
| **Orchestrator** | `search → fetch → parse → index → retrieve → score` | Python + FastAPI |
| **Document Parser** | PDF tables, charts, multi-column layouts | LlamaParse (LlamaCloud) |
| **Vector Store** | Semantic search over document chunks | Qdrant |
| **Relational DB** | Sessions, stock recommendations, document metadata | Supabase (PostgreSQL) |
| **Web Search** | Find relevant reports and filings | Tavily API + DuckDuckGo fallback |
| **Financial Data** | Real-time prices, P/E, margins, growth | yfinance |
| **Stock Scorer** | Weighted multi-factor scoring (fundamentals 30%, thematic 25%, risk 20%, momentum 15%, liquidity 10%) | Pydantic + yfinance |
| **LLM** | Thesis synthesis, stock extraction, structured output | OpenAI GPT-4o-mini (configurable) |

**Design choices:**
- **Supabase over Convex** — Supabase gives us managed PostgreSQL with a REST API, auth, and generous free tier. Convex is JS-native; our Python backend needs a first-class Postgres client.
- **Qdrant over pgvector** — Purpose-built vector DB with filterable HNSW, session-scoped collections, and better retrieval latency at scale.
- **LlamaParse over PyMuPDF** — Industry-leading financial document parsing (tables, charts, footnotes). Critical for 10-Ks and investor decks.
- **Agent finds documents itself** — No manual upload. The agent searches, downloads, and parses autonomously.

---

## Project Structure

```
basis/
├── README.md
├── Makefile
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── Dockerfile
│   ├── schema.sql          # Supabase tables
│   └── src/
│       ├── main.py         # FastAPI app
│       ├── config.py       # Pydantic settings
│       ├── agent.py        # Orchestrator
│       ├── db/
│       │   └── supabase_client.py
│       ├── models/
│       │   └── schemas.py  # Pydantic types
│       └── tools/
│           ├── document_fetcher.py   # Search + download PDFs
│           ├── document_parser.py    # LlamaParse wrapper
│           ├── vector_store.py       # Qdrant session manager
│           ├── stock_scorer.py       # Multi-factor scoring
│           ├── web_search.py         # Tavily / DDG
│           └── financial_data.py     # yfinance wrapper
├── frontend/
│   ├── package.json
│   ├── .env.local
│   ├── Dockerfile
│   ├── app/
│   │   ├── (chat)/
│   │   │   ├── page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── api/
│   │   │       └── chat/
│   │   │           └── route.ts      # Proxy to backend
│   │   └── layout.tsx
│   └── components/
│       └── chat/
│           └── shell.tsx             # Chat UI
├── docs/
│   ├── architecture.md     # ADR: framework, tool, design decisions
│   ├── failure_modes.md    # Where the agent breaks and how to fix
│   └── writeup.md          # Work trial write-up
├── eval/
│   ├── test_cases.json
│   ├── run_eval.py
│   └── metrics.py
└── tests/
    └── test_agent.py
```

---

## Deploy

**Free tier stack:**

| Layer | Service | Cost |
|-------|---------|------|
| Frontend | Vercel | Free |
| Backend API | Fly.io | Free (3 VMs, 3GB) |
| Vector DB | Qdrant Cloud | Free (1GB) |
| Relational DB | Supabase | Free (500MB) |

```bash
# Deploy backend + Qdrant to Fly.io
fly launch --dockerfile backend/Dockerfile
fly deploy

# Deploy frontend to Vercel
vercel --prod
```

---

## License

MIT
