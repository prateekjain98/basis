"""
Scoring logic for the eval suite.

Automated checks where possible; LLM-as-judge for qualitative dimensions.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict


class EvalResult:
    """Result of running one test case."""

    def __init__(self, test_id: str, passed: bool, score: float, notes: str):
        self.test_id = test_id
        self.passed = passed
        self.score = score
        self.notes = notes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "passed": self.passed,
            "score": self.score,
            "notes": self.notes,
        }


def check_thesis_structure(thesis_text: str) -> Dict[str, bool]:
    """Check if the output contains required thesis sections."""
    text = thesis_text.lower()
    return {
        "has_thesis": "##" in thesis_text or "investment" in text,
        "has_rationale": "rationale" in text or "bull" in text,
        "has_risks": "risk" in text or "bear" in text,
        "has_conviction": "conviction" in text,
    }


def check_grounding(thesis_text: str, raw_data: Dict[str, Any]) -> bool:
    """
    Naive hallucination check: extract dollar values and percentages from thesis
    and verify they appear in raw tool output.
    """
    import re

    # Extract $X, X%, $X.Y patterns
    numbers = re.findall(r"\$[\d,]+\.?\d*|[\d]+\.[\d]+%?|\d+%", thesis_text)

    # Flatten raw_data to a string for search
    raw_str = json.dumps(raw_data)

    false_claims = 0
    for num in numbers:
        # Strip $ and commas for fuzzy match
        clean = num.replace("$", "").replace(",", "").replace("%", "")
        if clean and clean not in raw_str:
            false_claims += 1

    # Allow up to 1 unmatched number (could be from LLM knowledge or rounding)
    return false_claims <= 1


def score_test_case(
    test_case: Dict[str, Any],
    thesis_text: str,
    raw_data: Dict[str, Any],
    tools_called: list[str],
) -> EvalResult:
    """Score a single test case against its rubric."""
    rubric = test_case.get("rubric", {})
    structure = check_thesis_structure(thesis_text)
    grounded = check_grounding(thesis_text, raw_data)

    checks = {
        **structure,
        "grounded_in_data": grounded,
        "graceful_degradation": "acknowledges" in thesis_text.lower() or "gap" in thesis_text.lower(),
        "acknowledges_ambiguity": "unclear" in thesis_text.lower() or "ambigu" in thesis_text.lower(),
        "acknowledges_data_gap": "data" in thesis_text.lower() and "gap" in thesis_text.lower(),
        "thesis_still_generated": len(thesis_text) > 200,
        "recalls_context": "previous" in thesis_text.lower() or "session" in thesis_text.lower(),
        "comparison_made": "compare" in thesis_text.lower() or "versus" in thesis_text.lower() or "vs" in thesis_text.lower(),
        "no_hallucinated_financials": grounded,
    }

    total = len(rubric)
    passed_count = 0
    failures = []

    for key, expected in rubric.items():
        actual = checks.get(key, False)
        if actual == expected:
            passed_count += 1
        else:
            failures.append(f"{key}: expected {expected}, got {actual}")

    score = passed_count / total if total > 0 else 0.0
    passed = score >= 0.75  # 75% threshold

    notes = " | ".join(failures) if failures else "All checks passed"
    return EvalResult(test_case["id"], passed, score, notes)
