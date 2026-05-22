"""Quick backtest: ThemeMapper vs Aschenbrenner's known holdings."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from src.tools.backtest import ASCHENBRENNER_HOLDINGS, validate_against_thesis
from src.tools.theme_mapper import ThemeMapper, THEME_ANCHORS

# Core themes that Aschenbrenner's thesis covers
ASCHENBRENNER_THEMES = [
    "solid oxide fuel cells for data center power",
    "gpu cloud infrastructure",
    "optical interconnects for AI clusters",
    "memory and storage for AI",
    "bitcoin mining with stranded energy",
    "data center operators",
    "semiconductor manufacturing",
    "nuclear power for data centers",
]

# Test anchor mappings only (fast, no web search)
print("=" * 60)
print("ThemeMapper ANCHOR backtest: Aschenbrenner themes")
print("=" * 60)

all_tickers = []
for theme in ASCHENBRENNER_THEMES:
    # Use anchor tickers directly
    tickers = []
    theme_lower = theme.lower()
    for keyword, ticker_list in THEME_ANCHORS.items():
        if keyword in theme_lower:
            tickers.extend(ticker_list)
    tickers = list(dict.fromkeys(tickers))  # dedupe preserve order
    all_tickers.extend(tickers)
    print(f"\nTheme: {theme}")
    print(f"  Anchor tickers: {tickers}")

unique_tickers = list(dict.fromkeys(all_tickers))
print(f"\n{'=' * 60}")
print(f"Total unique tickers from anchors: {len(unique_tickers)}")
print(f"Tickers: {sorted(unique_tickers)}")

result = validate_against_thesis(unique_tickers)
print(f"\n{'=' * 60}")
print("VALIDATION AGAINST ASCHENBRENNER HOLDINGS")
print(f"{'=' * 60}")
print(f"Match rate: {result['match_rate']:.0%} ({len(result['matches'])}/{len(unique_tickers)})")
print(f"Matches: {result['matches']}")
print(f"Missed holdings: {result['missed_holdings']}")
print(f"False positives: {result['false_positives']}")
