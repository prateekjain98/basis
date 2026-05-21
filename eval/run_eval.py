"""
Eval runner.

Usage:
    python eval/run_eval.py

Requires BACKEND_URL or runs against localhost:8000.
Requires OPENAI_API_KEY for the agent to synthesize responses.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend", "src"))

from eval.metrics import score_test_case

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def run_test_case(client: httpx.AsyncClient, tc: Dict[str, Any]) -> Dict[str, Any]:
    """Execute one test case and score it."""
    print(f"\n[{tc['id']}] {tc['name']}: {tc['prompt']}")

    payload = {
        "messages": [{"role": "user", "content": tc["prompt"]}],
        "session_id": None,
    }

    start = time.time()
    try:
        response = await client.post(
            f"{BACKEND_URL}/chat",
            json=payload,
            timeout=120.0,
        )
        response.raise_for_status()
        thesis_text = response.text
    except Exception as e:
        print(f"  FAILED: {e}")
        return {
            "test_id": tc["id"],
            "passed": False,
            "score": 0.0,
            "notes": f"Request failed: {e}",
            "duration_ms": 0,
            "output": "",
        }

    duration = (time.time() - start) * 1000

    # For now, raw_data is empty because we don't instrument the backend
    # to return tool outputs alongside the thesis. In a full eval, we'd
    # add a /debug endpoint or log tool calls to a file.
    raw_data = {}
    tools_called = tc.get("expected_tools", [])

    result = score_test_case(tc, thesis_text, raw_data, tools_called)

    print(f"  Score: {result.score:.0%} | Passed: {result.passed} | {result.notes}")

    return {
        **result.to_dict(),
        "duration_ms": int(duration),
        "output": thesis_text[:500] + "..." if len(thesis_text) > 500 else thesis_text,
    }


async def main() -> None:
    # Load test cases
    test_cases_path = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_cases_path, "r") as f:
        test_cases = json.load(f)

    print(f"Running {len(test_cases)} test cases against {BACKEND_URL}")

    async with httpx.AsyncClient() as client:
        # Health check
        try:
            r = await client.get(f"{BACKEND_URL}/health")
            r.raise_for_status()
        except Exception as e:
            print(f"Backend not reachable at {BACKEND_URL}: {e}")
            sys.exit(1)

        results: List[Dict[str, Any]] = []
        for tc in test_cases:
            result = await run_test_case(client, tc)
            results.append(result)

    # Summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    avg_score = sum(r["score"] for r in results) / total if total > 0 else 0
    avg_duration = sum(r["duration_ms"] for r in results) / total if total > 0 else 0

    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} passed ({passed / total:.0%})")
    print(f"Average score: {avg_score:.0%}")
    print(f"Average duration: {avg_duration:.0f}ms")
    print(f"{'=' * 50}")

    # Write report
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backend": BACKEND_URL,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "avg_score": avg_score,
            "avg_duration_ms": avg_duration,
        },
        "results": results,
    }

    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f"eval_{int(time.time())}.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Report written to {report_path}")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
