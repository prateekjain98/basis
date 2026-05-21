# Failure Modes

Where the agent breaks, why it breaks, and what it would take to fix it.

Failures are categorized by severity:
- **P0 — Blocking:** The agent cannot complete its core task
- **P1 — Degraded:** The agent completes the task but output quality is poor
- **P2 — Cosmetic:** Visual or UX issues that don't affect correctness

---

## P0 — Blocking

### 1. No working LLM provider

**What breaks:** The agent discovers and parses documents, then dies at the LLM synthesis step. Returns an empty thesis.

**Root cause:**
- OpenAI key exhausted $10 credit → 429 insufficient_quota
- Anthropic key returns 404 on all models → expired/revoked
- Vertex AI project has no model access → 404

**Current mitigation:** The agent catches the exception, returns a fallback thesis with no stocks, and logs the error. The user sees "LLM error" in the stream.

**Fix:**
- Add a local model path (Ollama with `mistral:latest` is already running on `localhost:11434`)
- Add OpenRouter or Together AI as a fallback provider (~$5 free credit)
- Effort: 2–3 hours to wire Ollama into `_llm_chat()` with JSON-mode prompting

### 2. Frontend crashes on empty model list

**What breaks:** `meraki.prateekjain.io` loads a blank white screen. Console: `Cannot read properties of undefined (reading 'id')`.

**Root cause:** `/api/models` returns `{models: []}`. `useActiveChat` in `frontend/hooks/use-active-chat.tsx` does `activeModels[0]` without a guard.

**Current mitigation:** None. The deployed site is currently broken.

**Fix:**
- Add `if (!activeModels.length) return defaultModel` guard in `use-active-chat.tsx`
- Or return a hardcoded model list from `/api/models` even without AI Gateway
- Effort: 15 minutes

### 3. Cloud Run → Qdrant Cloud 403 Forbidden

**What breaks:** On the deployed backend, vector indexing and search fail. The agent falls back to in-memory keyword search, which returns poor results.

**Root cause:** Cloud Run backend is missing the `QDRANT_API_KEY` environment variable. Only `QDRANT_URL` is set.

**Current mitigation:** `SessionVectorStore` detects `self.client is None` and falls back to `self._mem` (keyword search over stored strings).

**Fix:**
- Set `QDRANT_API_KEY` in Cloud Run environment variables
- Effort: 5 minutes (GCP console)

---

## P1 — Degraded

### 4. LLM returns markdown-wrapped JSON

**What breaks:** ~30% of GPT-4o-mini responses wrap JSON in markdown fences. `json.loads()` throws. The agent returns an empty thesis.

**Root cause:** The model ignores `response_format={"type": "json_object"}` about 30% of the time at low temperatures.

**Current mitigation:** `.removeprefix("```json")` and `.removeprefix("```")` before parsing. This is a hack.

**Fix:**
- Use `response_format={"type": "json_object"}` strictly and retry on parse failure
- Or switch to a model with stronger JSON adherence (Claude 3.5 Sonnet, GPT-4o)
- Effort: 30 minutes

### 5. yfinance rate-limits after ~20 tickers

**What breaks:** Stock scores show `None` across the board. The 5-factor rubric returns neutral 50s for all dimensions.

**Root cause:** Yahoo Finance blocks IPs after rapid sequential requests. No API key or authentication mechanism.

**Current mitigation:** All exceptions are caught. Missing fields default to 50/100. The agent continues with partial data.

**Fix:**
- Add request batching with 1-second delays between calls
- Add a fallback data source (Alpha Vantage for fundamentals, Polygon for prices)
- Effort: 2–3 hours

### 6. Follow-ups retrieve wrong context

**What breaks:** After a thesis on NVDA, asking "what about the risks?" retrieves passages about "AI risk management frameworks" instead of "risks of NVDA stock."

**Root cause:** Retrieval query is a naive blend of the last 4 messages. It does not understand that "risks" refers to the previously recommended stocks.

**Current mitigation:** The blended query includes message history, which helps ~60% of the time.

**Fix:**
- Extract stock tickers from the previous thesis and inject them into the follow-up retrieval query
- Or use a re-ranking model (Cohere Rerank) to score retrieved passages against the conversation context
- Effort: 2–4 hours

### 7. DDG search returns garbage without Tavily

**What breaks:** ~30% of downloaded "PDFs" are HTML landing pages, blog posts, or SEO spam. The parser returns empty text.

**Root cause:** DuckDuckGo search results are noisy. Without Tavily's curated search, many candidates are not real documents.

**Current mitigation:** URL scoring filters out obvious junk (login pages, Google Drive links). Magic-byte validation rejects non-PDFs. But some HTML pages masquerade as PDFs.

**Fix:**
- Add Tavily API key for curated search results
- Add content-type validation *before* full download (HEAD request)
- Effort: 1 hour

---

## P2 — Cosmetic

### 8. Qdrant collections grow unbounded

**What breaks:** Memory usage grows linearly with sessions. 50 sessions = 50 collections.

**Root cause:** Per-session collection design. No automatic cleanup on session deletion.

**Current mitigation:** `DELETE /sessions/{id}` drops both the Supabase rows and the Qdrant collection. The user must explicitly delete.

**Fix:**
- Add a nightly cron job to delete collections for sessions older than 30 days
- Or switch to a single collection with `session_id` in the payload
- Effort: 1–2 hours

### 9. Frontend stripped template still has cruft

**What breaks:** Build warnings from unused artifact components. Bundle size larger than necessary.

**Root cause:** The Vercel AI Chatbot template had artifacts, AI Gateway, auth, model selector. We stripped the visible parts but not all imports.

**Current mitigation:** Build succeeds. Warnings are non-fatal.

**Fix:**
- Audit and remove unused components and imports
- Effort: 1 hour

### 10. Same query, different results across days

**What breaks:** Evaluations are non-deterministic. Monday's "AI infrastructure" thesis uses different documents than Tuesday's.

**Root cause:** Web search results change daily. The document corpus is not cached between runs.

**Current mitigation:** Session stores exactly which documents were used. But there is no "rerun with cached docs" mode.

**Fix:**
- Add a `--use-cached-docs` flag to the eval runner that loads documents from a previous session
- Or mock the document fetcher in tests
- Effort: 2–3 hours
