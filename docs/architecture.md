# Architecture Decisions

This document records the design decisions behind Basis. Each section states the decision, the options considered, and the rationale.

---

## ADR-1: Task Selection — Thematic Investment Research

**Status:** Accepted

**Context:** The brief requires a conversational agent for a multi-step task with at least 2 tools and session memory, prioritizing reliability over complexity.

**Decision:** Build an agent that researches investment themes, discovers real documents, and returns scored stock recommendations with session memory for follow-ups.

**Rationale:**
- The task is inherently multi-step: search → fetch → parse → index → retrieve → score
- It naturally requires multiple distinct tools (document discovery, financial data, vector search)
- Session memory is meaningful: follow-ups should reuse the document corpus, not restart
- Financial data provides a clear correctness signal: hallucinated numbers are dangerous and detectable

**Consequences:**
- (+) Strong eval signal: we can verify if claimed financials match real data
- (+) Follow-ups have real utility: adjusting positions based on new questions
- (-) Requires live web search and PDF parsing — more failure modes than a closed-domain task

---

## ADR-2: Backend Framework — FastAPI + Pydantic

**Status:** Accepted

**Decision:** Use FastAPI with Pydantic models for the backend API.

**Options considered:**

| Option | Reason rejected |
|--------|-----------------|
| Flask + Marshmallow | No native async; no auto-generated OpenAPI docs |
| Django | Too heavy for a single-purpose agent API; ORM conflicts with Supabase decision |
| LangChain/LangGraph | See ADR-6 |

**Rationale:**
- The pipeline is I/O bound (web search, PDF download, LLM calls). FastAPI's native async/await is essential.
- Pydantic provides runtime validation and auto-generated OpenAPI schemas without extra code.
- The pipeline is linear and deterministic. No need for an agent framework's ReAct loop.

**Consequences:**
- (+) Clean API docs at `/docs` automatically
- (+) Type-safe request/response models
- (-) We write the orchestration logic manually in `agent.py`

---

## ADR-3: Database — Supabase over SQLAlchemy + Alembic

**Status:** Accepted

**Decision:** Use Supabase for session, document, and trade persistence.

**Context:** We initially started with SQLAlchemy + Alembic. Wrote models, connection pooling, migration files. Spent >1 hour debugging migration version conflicts before the schema was even stable.

**Rationale:**
- Supabase provides a Postgres instance with an auto-generated REST API. No ORM code needed.
- Schema managed via Supabase CLI migrations (`supabase migration new` → `supabase db push`).
- The Python client (`supabase-py`) is sync-only. We wrap calls in `asyncio.to_thread()`. This is ugly but obvious and debuggable.

**Consequences:**
- (+) Zero ORM boilerplate
- (+) Schema changes are one CLI command
- (-) Less type safety than SQLAlchemy ORM. We compensate with Pydantic schemas in `src/models/schemas.py`.
- (-) `asyncio.to_thread()` adds slight overhead per DB call

**Schema:**
```sql
thesis_sessions    -- id, user_query, theme, summary, conviction, created_at
documents          -- id, thesis_id, url, title, parsed_content, chunk_count
stock_recommendations -- id, thesis_id, ticker, name, entry_price, total_score, rationale
messages           -- id, session_id, role, content, created_at
```

---

## ADR-4: Vector Store — Qdrant over pgvector

**Status:** Accepted

**Decision:** Use Qdrant for document embeddings. One collection per session.

**Options considered:**

| Option | Reason rejected |
|--------|-----------------|
| pgvector (Supabase) | Shares RAM with OLTP; HNSW search slows past ~1M vectors |
| Pinecone | Requires separate account; pricing complexity |
| Chroma | In-process only; harder to deploy on Cloud Run |

**Rationale:**
- Qdrant is a single Docker container locally, or a managed cloud service.
- HNSW is the default index type. No tuning needed for our corpus size (~500 chunks/session).
- Per-session collections make deletion trivial (`DELETE collection`). A production setup would use one collection with `session_id` in the payload, but per-session is simpler and correct for this scope.

**Consequences:**
- (+) Fast semantic search out of the box
- (+) Easy local development with Docker
- (-) Per-session collections = linear memory growth. Mitigation: `DELETE /sessions/{id}` drops the collection.
- (-) Cloud Run → Qdrant Cloud requires `QDRANT_API_KEY` env var. Currently missing, causing 403 fallback to in-memory search.

---

## ADR-5: Document Parsing — LlamaParse + PyMuPDF Fallback

**Status:** Accepted

**Decision:** Use LlamaParse as primary parser, with PyMuPDF as fallback.

**Rationale:**
- PyMuPDF returns scrambled text on multi-column financial reports — table rows get interleaved with footnotes.
- LlamaParse is the only parser found that consistently preserves table structure and converts charts to markdown.
- Without a LlamaParse key, `DocumentParser.parse()` returns `None` and the pipeline falls back to PyMuPDF or web snippets. The agent does not crash.

**Consequences:**
- (+) High-quality structured text from complex PDFs
- (-) LlamaParse requires an API key and has usage limits
- (-) PyMuPDF fallback produces lower-quality output for tables

---

## ADR-6: Why Not LangChain / LangGraph

**Status:** Accepted

**Decision:** Do not use LangChain or LangGraph. Implement the pipeline in plain Python.

**Rationale — three reasons:**

**1. The pipeline is linear, not exploratory.**

LangChain's value is the ReAct loop — the agent decides "should I search? should I calculate?" Our pipeline is a fixed sequence:

```
search → fetch → parse → index → retrieve → score
```

There is no decision-making at each step. We always do all six. LangChain's abstractions add complexity without adding capability.

**2. Follow-ups don't need an agent framework.**

Session memory is 15 lines of code: load message history, blend it into the retrieval query, call the LLM again. LangChain's `ConversationBufferMemory` would wrap the same logic in 3 layers of abstraction.

**3. Debugging.**

When the LLM wraps JSON in markdown fences (~30% with GPT-4o-mini), we need to find where to add stripping logic. In plain Python, it's the line after `chat.completions.create()`. In LangChain, we'd dig through `JSONOutputParser` internals.

**When LangGraph would be worth it:**

If we added a second agent — e.g., a risk analyst that argues with the main researcher — then LangGraph's DAG and state management become worth the complexity. For a single linear pipeline, it's overkill.

**Consequences:**
- (+) Full visibility into every step
- (+) No framework lock-in
- (-) We write orchestration code manually

---

## ADR-7: Financial Data — yfinance

**Status:** Accepted

**Decision:** Use yfinance for live stock fundamentals.

**Options considered:**

| Option | Reason rejected |
|--------|-----------------|
| Bloomberg Terminal | $24k/year license |
| Alpha Vantage | Free tier: 5 req/min |
| Polygon.io | $199/mo minimum |

**Rationale:**
- yfinance is free, no API key, returns P/E, margins, growth, debt.
- The tradeoff: it scrapes Yahoo Finance, which blocks IPs after heavy use.
- The scorer catches all exceptions and returns partial data. Missing fields default to neutral (50/100).

**Consequences:**
- (+) Zero cost, zero API key management
- (-) Rate-limits after ~20 tickers in rapid succession
- (-) No SLA; Yahoo can change their HTML structure at any time

---

## ADR-8: Frontend — Next.js + Vercel AI SDK

**Status:** Accepted

**Decision:** Use Next.js 16 with the Vercel AI SDK for the chat UI.

**Context:** We started from the Vercel AI Chatbot starter template — full of features we don't need: AI Gateway, artifacts, auth, model selector, credit card alert popup.

**What we kept:**
- Chat shell and message threading components
- `useChat` hook for streaming SSE handling
- API route proxy pattern

**What we stripped:**
- Auth system (replaced with dummy auth for demo)
- AI Gateway references
- Artifact rendering
- Model selector
- Credit card alert

**Rationale:**
The Vercel AI SDK handles streaming, error states, and abort signals correctly. Re-implementing SSE parsing in raw React is error-prone.

**Consequences:**
- (+) Production-ready streaming chat UI with minimal code
- (-) Template still has unused imports and components causing build warnings

---

## ADR-9: LLM Provider — Multi-provider with OpenAI default

**Status:** Accepted

**Decision:** Support OpenAI, Anthropic, and Vertex AI. Default to OpenAI.

**Rationale:**
- OpenAI is the default because `gpt-4o-mini` supports JSON mode and is cheap.
- Anthropic and Vertex are wired in for redundancy — swapping providers is one env var change.
- All three use the same `_llm_chat()` abstraction. The agent code does not care which provider is active.

**Current status:**
- OpenAI: 429 insufficient_quota ($10 credit exhausted)
- Anthropic: 404 on all models (expired key)
- Vertex AI: 404 (no model access on project)

**Consequences:**
- (+) Provider redundancy with zero code changes
- (-) Currently no working provider in production. Fix: wire Ollama (`mistral:latest` on `localhost:11434`).

---

## ADR-10: Session Memory Design

**Status:** Accepted

**Decision:** Dual-layer session memory:

1. **Document corpus persistence:** Every document from the first turn is saved to Supabase and indexed in Qdrant. Follow-ups check for existing documents; if found, skip search/fetch/parse/index.

2. **Message history blending:** Follow-ups concatenate the last 4 messages into the retrieval query.

**Rationale:**
- It is cheap: no re-embedding, no re-searching
- It is reliable: the document corpus is the ground truth for the session
- It degrades gracefully: off-topic questions still search the existing corpus; the LLM falls back to general knowledge if needed

**Consequences:**
- (+) Fast follow-ups: ~2s vs ~30s for full document discovery
- (+) Consistent grounding: same documents across the session
- (-) Heuristic blending is fragile. Topic switches mid-session pollute retrieval context. A production system would use intent classification to decide whether to search new documents.
