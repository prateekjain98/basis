"""Load test: simulate N concurrent users hitting /chat.

Usage:
    python load_test.py --users 10 --queries queries.json

Each user sends a thesis query and waits for the full response.
Measures: success rate, avg latency, p95 latency, error rate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

DEFAULT_QUERIES = [
    "Investment thesis on AI infrastructure buildout",
    "What are the best renewable energy stocks",
    "Thesis on cybersecurity companies",
    "Investment opportunities in battery technology",
    "Thesis on semiconductor manufacturing",
    "Best stocks for data center power",
    "Investment thesis on gene therapy",
    "Thesis on copper mining for electrification",
    "Best fintech stocks to buy now",
    "Thesis on satellite internet companies",
]


async def send_chat(client: httpx.AsyncClient, user_id: int, query: str) -> Dict[str, Any]:
    """Send one chat request and collect the full streamed response."""
    payload = {
        "messages": [{"role": "user", "content": query}],
        "session_id": None,
    }
    start = time.time()
    try:
        response = await client.post(
            f"{BACKEND_URL}/chat",
            json=payload,
            timeout=300.0,
        )
        response.raise_for_status()
        text = response.text
        duration = time.time() - start
        return {
            "user_id": user_id,
            "query": query,
            "success": True,
            "duration": duration,
            "chars": len(text),
            "error": None,
        }
    except Exception as e:
        duration = time.time() - start
        return {
            "user_id": user_id,
            "query": query,
            "success": False,
            "duration": duration,
            "chars": 0,
            "error": str(e)[:200],
        }


async def run_load_test(users: int, queries: List[str]) -> None:
    print(f"Load test: {users} concurrent users against {BACKEND_URL}")
    print(f"Total requests: {users}")
    print("-" * 60)

    async with httpx.AsyncClient() as client:
        # Health check
        try:
            r = await client.get(f"{BACKEND_URL}/health", timeout=10)
            r.raise_for_status()
            print("Backend health: OK")
        except Exception as e:
            print(f"Backend not reachable: {e}")
            sys.exit(1)

        # Launch all requests concurrently
        start = time.time()
        tasks = [
            send_chat(client, i, queries[i % len(queries)])
            for i in range(users)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_duration = time.time() - start

    # Process results
    successes = [r for r in results if isinstance(r, dict) and r["success"]]
    failures = [r for r in results if isinstance(r, dict) and not r["success"]]
    exceptions = [r for r in results if isinstance(r, Exception)]

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"Total time: {total_duration:.1f}s")
    print(f"Success: {len(successes)}/{users} ({len(successes)/users:.0%})")
    print(f"Failures: {len(failures)}/{users}")
    print(f"Exceptions: {len(exceptions)}/{users}")

    if successes:
        durations = [r["duration"] for r in successes]
        avg = sum(durations) / len(durations)
        p50 = sorted(durations)[len(durations) // 2]
        p95 = sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else avg
        print(f"\nLatency (successful only):")
        print(f"  Avg:  {avg:.1f}s")
        print(f"  p50:  {p50:.1f}s")
        print(f"  p95:  {p95:.1f}s")
        print(f"  Min:  {min(durations):.1f}s")
        print(f"  Max:  {max(durations):.1f}s")

    if failures:
        print(f"\nFailure details:")
        for r in failures:
            print(f"  User {r['user_id']}: {r['error']}")

    if exceptions:
        print(f"\nExceptions:")
        for e in exceptions:
            print(f"  {e}")

    # Save report
    out_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"load_test_{users}u_{int(time.time())}.json")
    with open(out_path, "w") as f:
        json.dump({
            "backend": BACKEND_URL,
            "users": users,
            "total_duration": round(total_duration, 1),
            "success_rate": len(successes) / users,
            "latency": {
                "avg": round(avg, 1) if successes else None,
                "p50": round(p50, 1) if successes else None,
                "p95": round(p95, 1) if successes else None,
            },
            "results": [r for r in results if isinstance(r, dict)],
        }, f, indent=2)
    print(f"\nReport saved to {out_path}")

    if len(successes) < users:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--users", type=int, default=10, help="Number of concurrent users")
    parser.add_argument("--queries", type=str, help="JSON file with query list")
    args = parser.parse_args()

    queries = DEFAULT_QUERIES
    if args.queries and os.path.exists(args.queries):
        with open(args.queries) as f:
            queries = json.load(f)

    asyncio.run(run_load_test(args.users, queries))
