# Evaluation Suite

The eval suite tests the agent on three dimensions from the brief:
1. **Task completion rate** — Does the agent produce a valid thesis with scored stocks?
2. **Hallucination on tool outputs** — Are financial claims grounded in real data?
3. **Graceful failure handling** — Does the agent degrade cleanly when tools fail?

---

## Test Cases

8 test cases cover the agent's core capabilities and edge cases:

| ID | Name | Prompt | What it tests |
|---|---|---|---|
| tc-01 | Simple ticker query | `"Thesis on NVDA"` | Basic tool use: financial data + web search |
| tc-02 | Thematic without ticker | `"Investment thesis on AI infrastructure buildout"` | Document discovery path |
| tc-03 | Follow-up in session | `"What are the key risks?"` (after NVDA thesis) | Session memory: recalls previous context |
| tc-04 | Ambiguous prompt | `"Is this a good buy?"` | Graceful degradation: no ticker, no theme |
| tc-05 | Bad ticker | `"Thesis on XYZFAKE123"` | Tool failure handling: yfinance returns nothing |
| tc-06 | International market | `"Thesis on Reliance Industries"` | Non-US ticker support |
| tc-07 | Multi-turn memory | `"Compare that to AMD"` (after NVDA thesis) | Comparison across session history |
| tc-08 | No search results | `"Thesis on a very obscure private company"` | Empty corpus handling |

---

## Metrics

### Automated Checks

`eval/metrics.py` implements three classes of checks:

**1. Thesis structure**
```python
check_thesis_structure(thesis_text) -> {
    "has_thesis": bool,      # Contains "##" header or "investment"
    "has_rationale": bool,   # Contains "rationale" or "bull"
    "has_risks": bool,       # Contains "risk" or "bear"
    "has_conviction": bool,  # Contains "conviction"
}
```

**2. Grounding (hallucination detection)**
```python
check_grounding(thesis_text, raw_data) -> bool
```
Extracts all `$X`, `X%`, and decimal numbers from the thesis and verifies they appear in the raw tool output. Allows 1 unmatched number (could be LLM knowledge or rounding).

**3. Rubric scoring**
Each test case defines a rubric of expected boolean checks. The score is the fraction of checks that pass. A test passes if score ≥ 75%.

---

## Running the Evals

### Prerequisites
- Backend running at `http://localhost:8000` (or set `BACKEND_URL`)
- `OPENAI_API_KEY` set (required for LLM synthesis)

### Run

```bash
cd eval
python run_eval.py
```

### Output

The runner prints per-test results and a summary:

```
Results: 6/8 passed (75%)
Average score: 82%
Average duration: 12400ms
```

A JSON report is written to `eval/outputs/eval_{timestamp}.json`.

---

## Unit Tests

`tests/test_agent.py` tests tool reliability without requiring a live LLM:

| Test | What it checks |
|---|---|
| `test_web_search_returns_results` | Web search returns a list |
| `test_web_search_graceful_on_total_failure` | No crash on nonsense query |
| `test_stock_scorer_returns_partial_on_failure` | Fake ticker returns `None` fields, not exception |
| `test_stock_scorer_populates_known_ticker` | AAPL returns real data from yfinance |
| `test_vector_store_lifecycle` | Index → query → delete works end-to-end |
| `test_document_fetcher_finds_pdfs` | Finds, scores, downloads real PDFs |
| `test_document_fetcher_scoring` | Scoring logic produces monotonic rankings |

Run:
```bash
cd backend && pytest ../tests/test_agent.py -v
```

---

## Current Results

**Blocked by LLM quota.** The eval runner requires a working LLM provider to synthesize theses. As of the last run:

- OpenAI: 429 insufficient_quota
- Anthropic: 404 (expired key)
- Vertex AI: 404 (no model access)

**Unit tests pass:** 6/7 (vector store test is skipped without a real OpenAI key for embeddings).

**To run evals without spending API credits:**
1. Wire Ollama (`mistral:latest` on `localhost:11434`) into `backend/src/agent.py::_llm_chat()`
2. Disable JSON mode for local models (use regex extraction instead)
3. Re-run `python eval/run_eval.py`

---

## Known Eval Gaps

1. **Raw data instrumentation:** `check_grounding()` receives empty `raw_data` because the backend does not return tool outputs alongside the thesis. A `/debug` endpoint or structured logging would fix this.

2. **Non-determinism:** Web search results change daily. The same test case may pass on Monday and fail on Tuesday if the discovered documents differ. Mocking the fetcher or adding a `--use-cached-docs` flag would make evals deterministic.

3. **No human eval:** Automated checks catch structure and grounding, but not thesis quality. A human rater would score: "Is this actually a good investment thesis?" We have not built this.
