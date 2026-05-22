"""Test ThemeMapper web search fallback for themes with no anchors."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from src.tools.theme_mapper import ThemeMapper

tm = ThemeMapper()

# Themes that have NO anchor mappings — should fall back to web search
NO_ANCHOR_THEMES = [
    "quantum computing hardware",
    "autonomous trucking logistics",
    "vertical farming agriculture",
    "carbon capture technology",
    "hydrogen fuel for aviation",
]

print("=" * 70)
print("WEB SEARCH FALLBACK TEST")
print("=" * 70)

for theme in NO_ANCHOR_THEMES:
    mapped = tm.map_themes([theme], max_results_per_theme=3)
    tickers = [m["ticker"] for m in mapped]
    print(f"\n[{theme}]")
    print(f"  Tickers: {tickers}")
    if tickers:
        print(f"  Status: Web search returned {len(tickers)} tickers")
    else:
        print(f"  Status: No tickers found (web search may have failed)")
