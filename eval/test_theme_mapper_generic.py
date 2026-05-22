"""Generic ThemeMapper test suite — diverse sectors and themes.

Usage:
    python test_theme_mapper_generic.py          # full test with web search
    python test_theme_mapper_generic.py --fast   # anchor-only (fast)
"""

from __future__ import annotations

import os
import sys
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from src.tools.theme_mapper import ThemeMapper, THEME_ANCHORS

tm = ThemeMapper()

# Diverse test themes across sectors
TEST_CASES = [
    # AI / tech
    {"theme": "solid oxide fuel cells for data centers", "expected": {"BE", "PLUG"}},
    {"theme": "gpu cloud infrastructure providers", "expected": {"CRWV", "NVDA"}},
    {"theme": "optical interconnects for AI clusters", "expected": {"LITE", "COHR"}},
    {"theme": "bitcoin mining with renewable energy", "expected": {"IREN", "CLSK"}},
    {"theme": "memory chips for AI servers", "expected": {"SNDK", "MU"}},

    # Energy
    {"theme": "nuclear power for electricity grid", "expected": {"CEG", "BWXT"}},
    {"theme": "solar panel manufacturers", "expected": {"ENPH", "FSLR"}},
    {"theme": "battery technology for electric vehicles", "expected": {"TSLA", "QS"}},

    # Biotech / healthcare
    {"theme": "gene therapy companies", "expected": {"REGN", "VRTX"}},
    {"theme": "pharmaceutical drug discovery", "expected": {"JNJ", "PFE"}},

    # Cybersecurity
    {"theme": "zero trust cybersecurity platforms", "expected": {"ZS", "CRWD"}},
    {"theme": "enterprise firewall and security", "expected": {"PANW", "FTNT"}},

    # Space
    {"theme": "satellite internet and launch", "expected": {"ASTS", "RKLB"}},

    # Fintech
    {"theme": "digital payments and fintech", "expected": {"SQ", "PYPL"}},

    # Commodities
    {"theme": "lithium mining for batteries", "expected": {"ALB", "SQM"}},
    {"theme": "copper mining for electrification", "expected": {"FCX", "SCCO"}},

    # Edge cases — themes with no anchors
    {"theme": "quantum computing hardware", "expected": set()},
    {"theme": "autonomous trucking logistics", "expected": set()},
]


def run_tests(fast: bool = False):
    print("=" * 70)
    print(f"GENERIC THEME MAPPER TEST SUITE (mode: {'anchor-only' if fast else 'full'})")
    print(f"Total themes: {len(TEST_CASES)}")
    print("=" * 70)

    results = []
    total_expected = 0
    total_matched = 0

    for tc in TEST_CASES:
        theme = tc["theme"]
        expected = tc["expected"]

        if fast:
            # Skip web search; test anchors only
            mapped = tm._anchor_tickers(theme, max_results=3)
            actual = set(mapped)
        else:
            mapped = tm.map_themes([theme], max_results_per_theme=3)
            actual = {m["ticker"] for m in mapped}

        matches = actual & expected
        false_positives = actual - expected
        misses = expected - actual

        total_expected += len(expected)
        total_matched += len(matches)

        if not expected:
            status = "OK" if not actual else "NOISE"
        elif matches == expected:
            status = "PASS"
        elif matches:
            status = "PARTIAL"
        else:
            status = "FAIL"

        results.append({
            "theme": theme,
            "expected": sorted(expected),
            "actual": sorted(actual),
            "matches": sorted(matches),
            "misses": sorted(misses),
            "false_positives": sorted(false_positives),
            "status": status,
        })

        print(f"\n[{status}] {theme}")
        print(f"  Expected: {sorted(expected)}")
        print(f"  Actual:   {sorted(actual)}")
        if misses:
            print(f"  Missed:   {sorted(misses)}")
        if false_positives:
            print(f"  False +:  {sorted(false_positives)}")

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}/{len(results)}")

    recall = total_matched / max(1, total_expected)
    print(f"\n  Anchor recall: {total_matched}/{total_expected} = {recall:.0%}")
    print(f"  Anchor themes covered: {len(THEME_ANCHORS)}")

    # Save results
    out_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    suffix = "_fast" if fast else "_full"
    out_path = os.path.join(out_dir, f"theme_mapper_generic{suffix}.json")
    with open(out_path, "w") as f:
        json.dump({
            "summary": {
                "total_tests": len(results),
                "status_counts": status_counts,
                "anchor_recall": recall,
                "anchor_themes": len(THEME_ANCHORS),
                "mode": "anchor-only" if fast else "full",
            },
            "results": results,
        }, f, indent=2)
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run anchor-only tests (no web search)")
    args = parser.parse_args()
    run_tests(fast=args.fast)
