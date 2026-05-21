# Failure Modes

## What Actually Breaks

### 1. DDG search returns landing pages, not PDFs

**What happened:** I ran the document fetcher on "AI infrastructure" and the first 10 results were LinkedIn posts, company homepages, and SEO blogspam. None were actual PDFs. The old code blindly downloaded HTML files with `.pdf` extensions and then LlamaParse choked on them.

**Current fix:** The new `DocumentFetcher` scores every URL before downloading. It checks the path for `.pdf`, the domain against a trusted list, and validates the `Content-Type` header. It also runs 4 different search queries and deduplicates. Even with all this, maybe 10% of candidates are real usable PDFs.

**Still broken:** Some servers (like Intel's CDN) return 403 to non-browser user agents. We lose those. No fix yet — would need rotating proxies or a real browser.

### 2. LLM returns garbage JSON

**What happened:** GPT-4o-mini wrapped its JSON response in markdown fences (```json ... ```) about 30% of the time in my testing. `json.loads()` threw a `JSONDecodeError` and the agent returned an empty stock list.

**Current fix:** Strip ````json`, ````, and whitespace before parsing. Wrap in try/except so the user at least sees an error message in the stream instead of a 500.

**Still broken:** If the LLM invents a ticker symbol (e.g., "DeepSeek" → "DSK"), yfinance returns no data and the stock gets a score of 0 across all dimensions. No validation against a real ticker database yet.

### 3. yfinance blocks requests

**What happened:** After scoring ~20 stocks in a row during testing, yfinance started returning 403s. Yahoo Finance rate-limits by IP. The scores all showed `None` and the total calculation produced `nan`.

**Current fix:** The scorer catches all exceptions and returns a `FinancialMetrics` object with whatever fields it managed to fetch. The score calculation handles `None` gracefully — missing data just means a neutral 50 on that dimension.

**Still broken:** No fallback data source. If yfinance bans the IP, every stock gets mediocre scores. Polygon.io or Finnhub would help but both need API keys.

### 4. Qdrant collection grows unbounded

**What happened:** Each session gets its own Qdrant collection (`session_<uuid>`). After 50 test sessions I had 50 collections with ~500 chunks each. Qdrant memory usage grew linearly. On the free tier this would hit the 1GB limit fast.

**Current fix:** The `DELETE /sessions/{id}` endpoint drops the collection. Users can clean up manually.

**Still broken:** No automatic TTL or cleanup. A production version should use a single collection with a `session_id` filter instead of per-session collections.

### 5. Follow-up questions are context-dependent but fragile

**What happened:** I asked "invest in AI" then "what about the risks?" The agent retrieved chunks about "AI risk management frameworks" from the indexed documents instead of understanding I meant "risks of the stocks you just recommended."

**Current fix:** For follow-ups, the retrieval query is constructed from the last 4 messages + the current question. This gives the vector search more context than just the latest query.

**Still broken:** If the user asks something completely unrelated in a follow-up ("btw what's the weather"), the agent still tries to answer it using the document corpus. No intent detection to bail out.

### 6. Parallel downloads hang

**What happened:** The first version of `DocumentFetcher` used `ThreadPoolExecutor` without timeouts on `future.result()`. One URL (a broken CDN) hung forever and the whole agent stalled.

**Current fix:** 20-second timeout per future, 120-second timeout on `as_completed()`.

**Still broken:** Some servers accept the connection but send 1 byte per second to keep it alive. The requests library's read timeout doesn't catch this well. Would need socket-level timeouts.

### 7. The same query gives different results every time

**What happened:** Not really a failure, but worth documenting. Web search results change daily. The "best" PDF for "AI infrastructure" on Monday might be a Goldman report; on Tuesday it might be a blog post. This means evals are non-deterministic.

**Mitigation:** The session stores exactly which documents were used, so you can at least inspect the source material. For reproducible evals you'd need a "rerun with cached docs" mode.
