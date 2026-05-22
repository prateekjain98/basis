"""End-to-end test: call /chat with Aschenbrenner query, compare to known holdings."""

from __future__ import annotations

import json
import os
import re
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from src.tools.backtest import validate_against_thesis, ASCHENBRENNER_HOLDINGS

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
QUERY = "What are the best stocks according to Aschenbrenner Situational Awareness thesis"


def extract_tickers(text: str) -> list[str]:
    """Extract ticker symbols from agent output text."""
    # Match tickers in markdown tables or inline
    patterns = [
        re.compile(r'\|\s*([A-Z]{1,5})\s*\|'),  # table cells
        re.compile(r'\b([A-Z]{2,5})\b'),  # uppercase words
    ]
    tickers = []
    for pat in patterns:
        tickers.extend(pat.findall(text))
    # Filter false positives
    fp = {"AI", "CEO", "USA", "NYSE", "NASDAQ", "ETF", "IPO", "GDP", "FED", "SEC", "LLM"}
    return list(dict.fromkeys([t for t in tickers if t not in fp]))


async def run():
    async with httpx.AsyncClient() as client:
        # Health check
        r = await client.get(f"{BACKEND_URL}/health", timeout=10)
        r.raise_for_status()
        print(f"Backend OK: {BACKEND_URL}")

        print(f"\nQuery: {QUERY}")
        print("-" * 60)

        start = time.time()
        response = await client.post(
            f"{BACKEND_URL}/chat",
            json={"messages": [{"role": "user", "content": QUERY}], "session_id": None},
            timeout=300.0,
        )
        response.raise_for_status()
        text = response.text
        duration = time.time() - start

        print(f"Response received in {duration:.1f}s ({len(text)} chars)")
        print("\n--- FULL RESPONSE ---")
        print(text)
        print("--- END RESPONSE ---\n")

        tickers = extract_tickers(text)
        print(f"Extracted tickers: {tickers}")

        result = validate_against_thesis(tickers)
        print(f"\n{'=' * 60}")
        print("VALIDATION AGAINST ASCHENBRENNER HOLDINGS")
        print(f"{'=' * 60}")
        print(f"Match rate: {result['match_rate']:.0%} ({len(result['matches'])}/{len(tickers)})")
        print(f"Matches: {result['matches']}")
        print(f"Missed holdings: {result['missed_holdings']}")
        print(f"False positives: {result['false_positives']}")

        # Save raw response
        out_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"e2e_aschenbrenner_{int(time.time())}.json")
        with open(out_path, "w") as f:
            json.dump({
                "query": QUERY,
                "duration_s": round(duration, 1),
                "response_text": text,
                "extracted_tickers": tickers,
                "validation": result,
            }, f, indent=2)
        print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
