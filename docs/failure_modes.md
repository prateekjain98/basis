# Failure Modes

This document catalogs every known way the Basis agent breaks in production, grouped by subsystem. Each entry follows the same structure so you can scan for severity, reproduce the failure, and understand the architectural root cause.

## Quick Reference

| # | Failure | Category | Severity | Status |
|---|---------|----------|----------|--------|
| 1 | [LLM synthesis dies with no provider](#1-llm-synthesis-dies-with-no-provider) | LLM Reliability | P0 — Blocking | Mitigated |
| 2 | [JSON mode ignored by local LLM](#2-json-mode-ignored-by-local-llm) | LLM Reliability | P1 — Degraded | Mitigated |
| 3 | [Embedding model unavailable](#3-embedding-model-unavailable) | LLM Reliability | P1 — Degraded | Mitigated |
| 4 | [Frontend white-screen on empty models](#4-frontend-white-screen-on-empty-models) | Frontend | P0 — Blocking | Fixed |
| 5 | [Streaming connection drops](#5-streaming-connection-drops) | Frontend | P1 — Degraded | Open |
| 6 | [DDG search returns non-PDFs](#6-ddg-search-returns-non-pdfs) | Document Pipeline | P1 — Degraded | Mitigated |
| 7 | [Retrieval misses follow-up intent](#7-retrieval-misses-follow-up-intent) | Retrieval & Context | P1 — Degraded | Open |
| 8 | [Session memory tests can't verify](#8-session-memory-tests-cant-verify) | Retrieval & Context | P1 — Degraded | Open |
| 9 | [yfinance rate-limits after ~20 tickers](#9-yfinance-rate-limits-after-20-tickers) | External APIs | P1 — Degraded | Mitigated |
| 10 | [Eval grounding check broken](#10-eval-grounding-check-broken) | Eval & Observability | P1 — Degraded | Open |
| 11 | [Qdrant Cloud 403 from Cloud Run](#11-qdrant-cloud-403-from-cloud-run) | Infrastructure | P0 — Blocking | Mitigated |
| 12 | [Qdrant collections grow unbounded](#12-qdrant-collections-grow-unbounded) | Infrastructure | P2 — Cosmetic | Open |
| 13 | [Non-deterministic eval results](#13-non-deterministic-eval-results) | Eval & Observability | P2 — Cosmetic | Open |

---

## 1. LLM synthesis dies with no provider

**Category:** LLM Reliability  
**Severity:** P0 — Blocking

### What goes wrong
The agent discovers documents, parses them, indexes chunks, then reaches the synthesis step and dies with an authentication or quota error. The user receives an empty thesis or a generic error message.

### Example
```
openai.RateLimitError: Error code: 429 - {'error': {'message': 'You exceeded your current quota...'}}
```
Anthropic and Vertex AI return 404s because the keys are expired or the model endpoint is unreachable.

### Root cause
The `_llm_chat()` method tries OpenAI first, then Anthropic, then Vertex AI. All three are dead:
- OpenAI: $10 credit exhausted → 429 `insufficient_quota`
- Anthropic: API key returns 404 (organization not found or key revoked)
- Vertex AI: Model access not provisioned → 404

There is no local fallback in the provider chain.

### Impact
- First-turn queries return no thesis
- Follow-up queries return no response
- Entire agent is unusable without a working cloud key

### Current mitigation
Ollama (`mistral:latest` on `localhost:11434`) is wired in via `OPENAI_BASE_URL=http://localhost:11434/v1`. The OpenAI client is tricked into talking to Ollama. This works for local development but not in the deployed Cloud Run container (no Ollama there).

### Proposed fix
1. Ship Ollama as a sidecar in Cloud Run or switch to a hosted open-weight model (e.g., Groq with `llama3-8b`).
2. Add a provider health-check at startup so the agent fails fast with a clear message instead of dying mid-pipeline.

**Effort:** 2–4 hours

---

## 2. JSON mode ignored by local LLM

**Category:** LLM Reliability  
**Severity:** P1 — Degraded

### What goes wrong
The LLM is asked to return structured JSON (`response_format={"type": "json_object"}`). Instead, it returns markdown-fenced JSON:

```markdown
```json
{
  "thesis": "...",
  "stocks": [...]
}
```
```

### Example
```python
json.loads(raw)  # raises json.JSONDecodeError
```

### Root cause
Ollama's API does not support OpenAI's `response_format` parameter. Mistral 7B is not instruction-tuned for strict JSON output. The model sees the system prompt asking for JSON but wraps it in markdown fences ~30% of the time.

### Impact
- Parse errors cause the agent to return a fallback text response instead of structured data
- Stock scoring step is skipped (no JSON to extract tickers from)
- User sees a plain-text paragraph instead of a scored thesis

### Current mitigation
```python
raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```")
```
This strips fences before parsing. It is fragile and breaks if the model adds extra whitespace or language tags.

### Proposed fix
1. Use Ollama's native `format: "json"` option instead of OpenAI compatibility shim.
2. Add a retry loop: on `JSONDecodeError`, re-prompt with "Return ONLY raw JSON, no markdown."
3. Switch to a model with better instruction following (e.g., `llama3.1:8b` or `qwen2.5`).

**Effort:** 1–2 hours

---

## 3. Embedding model unavailable

**Category:** LLM Reliability  
**Severity:** P1 — Degraded

### What goes wrong
Vector indexing fails because the embedding endpoint returns 404. The system falls back to in-memory keyword search.

### Example
```
POST http://localhost:11434/v1/embeddings
404 — model "text-embedding-3-small" not found
```

### Root cause
The code uses `text-embedding-3-small` (OpenAI's model) even when talking to Ollama. Ollama does not host that model. The embedding call goes through the same `OPENAI_BASE_URL` shim but the model name is wrong.

### Impact
- No dense vector search. Retrieval quality drops significantly.
- Keyword fallback matches on exact token overlap; synonyms and paraphrases are missed.
- Thesis quality degrades because relevant document chunks are not surfaced.

### Current mitigation
`SessionVectorStore` falls back to an in-memory list of chunks with keyword matching when Qdrant or embeddings fail.

### Proposed fix
1. Use Ollama's embedding endpoint with a local model like `nomic-embed-text`.
2. Make the embedding model name configurable per provider.

**Effort:** 1–2 hours

---

## 4. Frontend white-screen on empty models

**Category:** Frontend  
**Severity:** P0 — Blocking

### What goes wrong
The UI renders a blank white screen. Console shows:
```
TypeError: Cannot read properties of undefined (reading 'id')
    at useActiveChat (use-active-chat.tsx:...)
```

### Root cause
`/api/models` was returning `{models: []}`. The `useActiveChat` hook does `activeModels[0].id` without checking if the array is empty.

### Impact
- Entire frontend crashes before any user interaction
- Happens whenever the backend model list endpoint is empty or slow

### Current mitigation
`/api/models` now returns a hardcoded model:
```typescript
{ models: [{ id: "mistral:latest", name: "Mistral (Local)", provider: "ollama" }] }
```

### Proposed fix
Add a null-guard in `useActiveChat` so the hook degrades gracefully even if the endpoint returns an empty array.

**Effort:** 15 minutes

---

## 5. Streaming connection drops

**Category:** Frontend  
**Severity:** P1 — Degraded

### What goes wrong
The frontend shows "Connection closed" mid-response. The streamed thesis is truncated.

### Root cause
Unknown. Possible causes:
- Cloud Run request timeout (default 5 minutes)
- Ollama closes the connection when generation is slow
- Frontend `EventSource` or fetch abort logic triggers early

### Impact
- User sees partial thesis, no stock scores
- Looks like the agent failed when it may have succeeded on the backend

### Current mitigation
None. User must refresh and retry.

### Proposed fix
1. Add structured logging to the backend stream generator to see where it stops.
2. Add a frontend reconnection attempt with `retry` logic.
3. Consider switching from raw text stream to SSE with explicit `done` events.

**Effort:** 2–3 hours

---

## 6. DDG search returns non-PDFs

**Category:** Document Pipeline  
**Severity:** P1 — Degraded

### What goes wrong
The document fetcher downloads HTML landing pages, paywalls, or SEO spam instead of actual PDFs. The parser then fails to extract text.

### Example
```
Downloaded: https://example.com/whitepaper (2.3 MB)
Magic bytes: 3c 21 44 4f 43...  → HTML, not PDF
Validation failed. Skipping.
```

### Root cause
DuckDuckGo results do not guarantee file type. Result titles often say "PDF" but link to landing pages. The URL scoring heuristic (`url.endswith(".pdf")`, domain authority) is not strong enough.

### Impact
- Document corpus is smaller than expected
- Agent may synthesize from fewer sources, reducing thesis quality
- Wasted bandwidth and parse time on garbage documents

### Current mitigation
1. URL scoring filters out known junk domains.
2. Magic-byte validation rejects non-PDFs after download.
3. Only top-N scored documents are kept.

### Proposed fix
1. Add `Content-Type` header check before downloading the body.
2. Integrate Tavily or SerpAPI for higher-quality search results with direct PDF links.
3. Add a per-source reliability score learned from past fetches.

**Effort:** 2–3 hours

---

## 7. Retrieval misses follow-up intent

**Category:** Retrieval & Context  
**Severity:** P1 — Degraded

### What goes wrong
After a thesis on NVDA, the user asks "what about risks?". The retriever searches for "what about risks?" instead of "NVDA stock risks", returning generic AI risk management frameworks instead of NVDA-specific risks.

### Example
**User:** "what about risks?"  
**Retrieval query:** "what about risks?" (blended from last 4 messages)  
**Top chunk:** "AI Risk Management Frameworks for Enterprises"  
**Expected:** "NVDA faces competition from AMD and supply chain concentration risk"

### Root cause
Follow-up retrieval blends the last 4 messages into a query string. There is no entity resolution: the system does not know "risks" refers to previously recommended stocks. No stock tickers are injected into the follow-up query.

### Impact
- Follow-up answers feel generic and disconnected from the original thesis
- User must repeat stock names explicitly to get relevant context

### Current mitigation
None. The heuristic blending is hard-coded.

### Proposed fix
1. Extract entities (stock tickers, company names) from the first-turn thesis and persist them in session state.
2. Inject those entities into follow-up retrieval queries automatically.
3. Use a re-ranker (e.g., Cohere Rerank) to boost chunks that mention the same tickers.

**Effort:** 3–4 hours

---

## 8. Session memory tests can't verify

**Category:** Retrieval & Context  
**Severity:** P1 — Degraded

### What goes wrong
Test cases tc-03 and tc-07 (session memory) always fail in the eval suite because the runner creates a fresh session per test. There is no way to test multi-turn memory.

### Example
```python
# run_eval.py
for case in test_cases:
    session_id = None  # fresh session every time
    response = await chat(case["query"], session_id=session_id)
```

### Root cause
The eval runner is designed for single-turn unit tests. It does not support passing a session ID from one test case to the next.

### Impact
- Session memory is not automatically tested
- Regressions in follow-up handling go undetected

### Current mitigation
Manual testing only.

### Proposed fix
1. Add a `session_id` field to test case definitions in `test_cases.json`.
2. Group test cases by session ID in the runner so tc-03 follows tc-01 in the same session.
3. Add an assertion that checks whether the response references documents or stocks from earlier turns.

**Effort:** 2–3 hours

---

## 9. yfinance rate-limits after ~20 tickers

**Category:** External APIs  
**Severity:** P1 — Degraded

### What goes wrong
The 5-factor stock scorer fetches financial data from Yahoo Finance. After ~20 tickers in rapid succession, yfinance returns empty DataFrames or throws `HTTPError: 429`.

### Example
```python
yf.Ticker("NVDA").info  # returns {} after rate limit
# Score defaults to neutral 50/100 for all factors
```

### Root cause
Yahoo Finance has no official API. yfinance scrapes Yahoo's internal endpoints. Rapid sequential requests trigger IP-based rate limiting.

### Impact
- Stock scores become neutral (50/100) instead of data-driven
- Thesis conviction may be mis-calibrated
- User cannot tell that scores are fallback values

### Current mitigation
1. Catch exceptions and return partial data.
2. Missing fields default to neutral scores (50/100).
3. Stock is still included in the thesis but with a disclaimer.

### Proposed fix
1. Batch requests with 1-second delays between tickers.
2. Add a cache layer (Redis or in-memory TTL) so repeated tickers in the same session don't re-fetch.
3. Add a fallback data source (e.g., Financial Modeling Prep free tier).

**Effort:** 2–3 hours

---

## 10. Eval grounding check broken

**Category:** Eval & Observability  
**Severity:** P1 — Degraded

### What goes wrong
`check_grounding()` in `eval/metrics.py` always passes because `raw_data` is empty. The check is supposed to verify that numbers in the thesis match tool outputs.

### Example
```python
def check_grounding(thesis, raw_data):
    nums = extract_numbers(thesis)
    for n in nums:
        if n not in raw_data:  # raw_data is always []
            return False
    return True  # always True
```

### Root cause
The backend does not instrument tool outputs into the response payload. `raw_data` is never populated.

### Impact
- Grounding metric is always 100%, giving false confidence
- Hallucinated numbers are not caught by the eval suite

### Current mitigation
None. The metric is effectively disabled.

### Proposed fix
1. Instrument the agent to collect all tool outputs (yfinance data, retrieved chunks) into a `raw_data` field.
2. Return `raw_data` as a hidden field in the API response or log it to Supabase.
3. Update `check_grounding()` to read from the instrumented source.

**Effort:** 3–4 hours

---

## 11. Qdrant Cloud 403 from Cloud Run

**Category:** Infrastructure  
**Severity:** P0 — Blocking

### What goes wrong
Vector indexing and search fail on the deployed backend. The system falls back to in-memory keyword search.

### Example
```
qdrant_client.http.exceptions.UnexpectedResponse: 403 Forbidden
```

### Root cause
Cloud Run container is missing the `QDRANT_API_KEY` environment variable. Qdrant Cloud rejects unauthenticated requests.

### Impact
- Deployed backend has no vector search
- Retrieval quality is significantly worse than local development
- Users get keyword-matched chunks instead of semantic search

### Current mitigation
`SessionVectorStore` detects the Qdrant failure and falls back to in-memory storage with keyword matching.

### Proposed fix
Set `QDRANT_API_KEY` in the Cloud Run service configuration.

**Effort:** 5 minutes

---

## 12. Qdrant collections grow unbounded

**Category:** Infrastructure  
**Severity:** P2 — Cosmetic

### What goes wrong
Each session creates a new Qdrant collection. Collections are never deleted automatically. Memory and storage grow linearly with usage.

### Root cause
Per-session collection design (ADR-4). No TTL or cleanup job.

### Impact
- Gradual storage growth
- Qdrant Cloud free tier may hit limits after heavy usage

### Current mitigation
`DELETE /sessions/{id}` drops the collection explicitly. Users (or a cron job) must call this.

### Proposed fix
Add a nightly Cloud Scheduler job that calls `DELETE /sessions/{id}` for sessions older than 30 days.

**Effort:** 1–2 hours

---

## 13. Non-deterministic eval results

**Category:** Eval & Observability  
**Severity:** P2 — Cosmetic

### What goes wrong
The same eval query produces different documents, different theses, and different scores on different days.

### Example
**Day 1:** tc-01 retrieves 3 PDFs about NVIDIA, thesis mentions H100 demand  
**Day 2:** tc-01 retrieves 2 PDFs (different URLs), thesis mentions Blackwell launch

### Root cause
Web search results change daily. DuckDuckGo ranking is not stable. The document corpus is not pinned.

### Impact
- Eval scores are not comparable across runs
- Regressions are hard to detect
- CI-like eval pipeline is not feasible

### Current mitigation
None.

### Proposed fix
1. Add a `--use-cached-docs` flag to `run_eval.py` that skips discovery and uses a pre-downloaded corpus.
2. Pin a set of reference documents in `eval/fixtures/` for stable regression testing.
3. Separate "live" evals (flaky, tests end-to-end) from "stable" evals (deterministic, tests logic).

**Effort:** 3–4 hours

---

## Severity Definitions

| Severity | Meaning | Example |
|----------|---------|---------|
| **P0 — Blocking** | Agent is unusable or returns no value | No LLM provider, frontend crash |
| **P1 — Degraded** | Agent works but output quality is poor | Wrong retrieval, rate limits, broken metrics |
| **P2 — Cosmetic** | Does not affect output quality | Storage growth, build warnings, flaky evals |

## How to reproduce any failure

1. Check the **Example** section for the exact error or behavior.
2. Run the backend locally with `OPENAI_BASE_URL=http://localhost:11434/v1` and `LLM_MODEL=mistral:latest`.
3. Use the eval runner: `cd eval && python run_eval.py --case <tc-id>`.
4. Inspect logs in `backend/src/agent.py` — the pipeline prints stage markers (`[DISCOVER]`, `[RETRIEVE]`, `[SYNTHESIZE]`).
