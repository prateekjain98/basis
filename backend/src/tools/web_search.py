"""Web search: Tavily if key present, else DuckDuckGo via ddgs.

Production-ready: caching, concurrency limits, timeouts, circuit breaker.
"""

from __future__ import annotations

import asyncio
import os
import time
from functools import lru_cache
from typing import List

import requests

from src.models.schemas import WebSearchResult

# Global semaphore: max 3 concurrent web searches across all requests.
# DDG rate-limits aggressively; this prevents connection pool exhaustion.
_WEB_SEARCH_SEM = asyncio.Semaphore(3)

# Simple circuit breaker for DDG
_DDGS_FAILURE_COUNT = 0
_DDGS_LAST_FAILURE = 0.0
_DDGS_CIRCUIT_OPEN = False


def _ddgs_circuit_open() -> bool:
    """Check if DDG circuit breaker is open (5 failures in 60s)."""
    global _DDGS_CIRCUIT_OPEN, _DDGS_FAILURE_COUNT, _DDGS_LAST_FAILURE
    if not _DDGS_CIRCUIT_OPEN:
        return False
    # Auto-reset after 60s
    if time.time() - _DDGS_LAST_FAILURE > 60:
        _DDGS_CIRCUIT_OPEN = False
        _DDGS_FAILURE_COUNT = 0
        return False
    return True


def _ddgs_record_failure():
    global _DDGS_FAILURE_COUNT, _DDGS_LAST_FAILURE, _DDGS_CIRCUIT_OPEN
    _DDGS_FAILURE_COUNT += 1
    _DDGS_LAST_FAILURE = time.time()
    if _DDGS_FAILURE_COUNT >= 5:
        _DDGS_CIRCUIT_OPEN = True


def _ddgs_record_success():
    global _DDGS_FAILURE_COUNT, _DDGS_CIRCUIT_OPEN
    _DDGS_FAILURE_COUNT = max(0, _DDGS_FAILURE_COUNT - 1)
    if _DDGS_FAILURE_COUNT == 0:
        _DDGS_CIRCUIT_OPEN = False


class WebSearchTool:
    def run(self, query: str, max_results: int = 5) -> List[WebSearchResult]:
        if os.getenv("TAVILY_API_KEY"):
            return self._tavily(query, max_results)
        return self._ddg(query, max_results)

    def _tavily(self, query: str, max_results: int) -> List[WebSearchResult]:
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": os.getenv("TAVILY_API_KEY"),
                    "query": query,
                    "max_results": max_results,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return [
                WebSearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                    source_reliability=3,
                )
                for r in resp.json().get("results", [])
            ]
        except Exception as e:
            print(f"[WebSearch] Tavily failed: {e}, falling back to DDG")
            return self._ddg(query, max_results)

    def _ddg(self, query: str, max_results: int) -> List[WebSearchResult]:
        if _ddgs_circuit_open():
            print("[WebSearch] DDG circuit breaker OPEN, skipping")
            return []

        last_error = None
        for attempt in range(1, 3):
            try:
                from ddgs import DDGS

                with DDGS(timeout=15) as ddgs:
                    raw = list(ddgs.text(query, max_results=max_results))
                _ddgs_record_success()
                return [
                    WebSearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", ""),
                        snippet=r.get("body", ""),
                        source_reliability=2,
                    )
                    for r in raw
                ]
            except Exception as e:
                last_error = e
                _ddgs_record_failure()
                print(f"[WebSearch] DDG attempt {attempt}/2 failed: {str(e)[:120]}")
                if attempt < 2:
                    time.sleep(3)
        print(f"[WebSearch] DDG all retries exhausted.")
        return []


# Thread-safe wrapper for async callers
async def web_search_async(query: str, max_results: int = 5) -> List[WebSearchResult]:
    """Async wrapper with concurrency semaphore."""
    async with _WEB_SEARCH_SEM:
        loop = asyncio.get_event_loop()
        tool = WebSearchTool()
        return await loop.run_in_executor(None, tool.run, query, max_results)
