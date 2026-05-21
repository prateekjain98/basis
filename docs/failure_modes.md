# failure modes

Things that are broken right now.

## 1. DDG search returns garbage

Ran `DocumentFetcher` on "AI infrastructure". First 10 results: LinkedIn posts, company homepages, SEO blogspam. Zero actual PDFs.

Fix: score URLs before downloading. Check `.pdf` extension, domain authority, `Content-Type` header. Still misses some — without Tavily, ~30% of candidates are HTML landing pages.

## 2. LLM returns markdown-wrapped JSON

GPT-4o-mini wraps JSON in fences ~30% of the time:

```json
{"theme": "...", "stocks": [...]}
```

`json.loads()` throws. Current fix is `.removeprefix("```json")` which is a hack. Should use `response_format={"type": "json_object"}`.

## 3. yfinance rate-limits

After ~20 tickers in rapid succession, Yahoo returns 403s. Scores show `None` across the board.

Fix: catch all exceptions, return partial data. Missing fields get neutral 50. No fallback data source yet.

## 4. Qdrant collections grow unbounded

Each session = one collection. 50 sessions = 50 collections. Memory usage grows linearly.

Fix: `DELETE /sessions/{id}` drops the collection. No automatic cleanup.

## 5. Follow-ups retrieve wrong context

Asked "invest in AI" then "what about the risks?" Retrieved passages about "AI risk management frameworks" instead of "risks of the stocks I just recommended."

Fix: blend last 4 messages into retrieval query. Still fragile — if the user asks something unrelated ("what's the weather"), the agent still searches the document corpus.

## 6. ThreadPoolExecutor hung on dead CDN

One download accepted TCP connection, sent zero bytes. `future.result()` blocked forever.

Fix: `timeout=20` per future, `timeout=120` on `as_completed()`. Some servers send 1 byte/sec to keepalive — `requests` read timeout doesn't catch this.

## 7. Same query, different results

Web search changes daily. Monday's "best" PDF might be a Goldman report; Tuesday's might be a blog post. Evals are non-deterministic.

Mitigation: session stores exactly which documents were used. No "rerun with cached docs" mode yet.

## 8. Frontend is stripped template cruft

The Vercel AI Chatbot template still has artifact code, AI Gateway references, and a credit card alert popup. Only the chat proxy in `route.ts` is actually used.
