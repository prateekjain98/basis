"""Comprehensive ThemeMapper simulations with various theme variations."""

from __future__ import annotations

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from src.tools.theme_mapper import ThemeMapper, THEME_ANCHORS
from src.tools.backtest import validate_against_thesis, ASCHENBRENNER_HOLDINGS

tm = ThemeMapper()

# Test suites
SUITES = {
    "aschenbrenner_exact": [
        "solid oxide fuel cells for data center power",
        "gpu cloud infrastructure",
        "optical interconnects for AI clusters",
        "memory and storage for AI",
        "bitcoin mining with stranded energy",
        "data center operators",
        "semiconductor manufacturing",
        "nuclear power for data centers",
    ],
    "aschenbrenner_vague": [
        "power for AI",
        "cloud compute",
        "fiber optics",
        "storage chips",
        "crypto mining",
        "hosting facilities",
        "chip making",
        "atomic energy",
    ],
    "aschenbrenner_verbose": [
        "Companies building on-site solid oxide fuel cell power plants for hyperscale data centers",
        "GPU-as-a-service cloud providers renting NVIDIA clusters to AI startups",
        "Suppliers of coherent optical transceivers and interconnects for AI training clusters",
        "Manufacturers of high-density NAND flash and SSD storage for AI workloads",
        "Bitcoin mining operators that co-locate with stranded natural gas or renewable energy",
        "Companies developing and operating specialized AI data center campuses",
        "Domestic semiconductor foundries and IDMs with advanced node capabilities",
        "Nuclear energy operators signing long-term power purchase agreements with tech companies",
    ],
    "edge_cases": [
        "quantum computing",  # no anchors
        "AI cybersecurity",   # no anchors
        "solid oxide fuel cells",  # direct keyword
        "gpu cloud",  # direct keyword
        "optical interconnect",  # direct keyword
    ],
}


def run_suite(name: str, themes: list[str]) -> dict:
    print(f"\n{'=' * 70}")
    print(f"SUITE: {name} ({len(themes)} themes)")
    print(f"{'=' * 70}")

    all_tickers = []
    theme_results = []

    for theme in themes:
        mapped = tm.map_themes([theme], max_results_per_theme=3)
        tickers = [m["ticker"] for m in mapped]
        all_tickers.extend(tickers)
        theme_results.append({"theme": theme, "tickers": tickers})
        print(f"  {theme[:60]:<60} → {tickers}")

    unique = list(dict.fromkeys(all_tickers))
    result = validate_against_thesis(unique)

    print(f"\n  Unique tickers: {len(unique)}")
    print(f"  Match rate: {result['match_rate']:.0%} ({len(result['matches'])}/{len(unique)})")
    print(f"  Matches: {result['matches']}")
    print(f"  Missed: {result['missed_holdings']}")
    print(f"  False positives: {result['false_positives']}")

    return {
        "suite": name,
        "themes": theme_results,
        "unique_tickers": unique,
        "validation": result,
    }


if __name__ == "__main__":
    all_results = []
    for name, themes in SUITES.items():
        all_results.append(run_suite(name, themes))

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY ACROSS ALL SUITES")
    print(f"{'=' * 70}")
    for r in all_results:
        v = r["validation"]
        print(f"  {r['suite']:<25} | match_rate={v['match_rate']:.0%} | "
              f"matches={len(v['matches'])} | missed={len(v['missed_holdings'])} | "
              f"fp={len(v['false_positives'])}")

    out_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "theme_simulations.json")
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved to {out_path}")
