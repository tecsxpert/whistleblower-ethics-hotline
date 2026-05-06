#!/usr/bin/env python3
"""
Performance tester — measures response times for all AI endpoints.

Usage:
    python perf_test.py              # 3 calls per endpoint (default)
    python perf_test.py --calls 10   # 10 calls per endpoint
"""

import argparse
import json
import statistics
import sys
import time

import requests

BASE_URL = "http://localhost:5000"
TARGET_MS = 2000

# ── Colour helpers ───────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

# ── Test definitions ─────────────────────────────────────────────────────

ENDPOINTS = [
    {
        "name": "GET /health",
        "method": "GET",
        "url": f"{BASE_URL}/health",
        "payload": None,
    },
    {
        "name": "POST /describe",
        "method": "POST",
        "url": f"{BASE_URL}/describe",
        "payload": {
            "text": "An employee reported that their manager has been falsifying expense "
            "reports for the past three months, totalling approximately $25,000."
        },
    },
    {
        "name": "POST /recommend",
        "method": "POST",
        "url": f"{BASE_URL}/recommend",
        "payload": {
            "text": "A senior engineer disclosed that safety protocols in the manufacturing "
            "plant are being bypassed to meet production targets."
        },
    },
    {
        "name": "POST /generate-report",
        "method": "POST",
        "url": f"{BASE_URL}/generate-report",
        "payload": {
            "text": "Multiple employees have reported persistent workplace harassment by a "
            "department head including verbal abuse and intimidation tactics."
        },
    },
    {
        "name": "POST /query",
        "method": "POST",
        "url": f"{BASE_URL}/query",
        "payload": {"query": "What is the procedure for reporting financial fraud?"},
    },
]


def run_test(endpoint: dict, num_calls: int) -> dict:
    """Run multiple calls against an endpoint and collect timing data."""
    times_ms: list[float] = []
    errors = 0
    fallbacks = 0

    for i in range(num_calls):
        try:
            start = time.time()
            if endpoint["method"] == "GET":
                resp = requests.get(endpoint["url"], timeout=30)
            else:
                resp = requests.post(
                    endpoint["url"],
                    json=endpoint["payload"],
                    timeout=30,
                )
            elapsed = (time.time() - start) * 1000

            if resp.status_code == 200:
                times_ms.append(elapsed)
                data = resp.json()
                if data.get("is_fallback"):
                    fallbacks += 1
            else:
                errors += 1

        except Exception:
            errors += 1

        if i < num_calls - 1:
            time.sleep(0.5)

    result = {
        "name": endpoint["name"],
        "calls": num_calls,
        "errors": errors,
        "fallbacks": fallbacks,
    }

    if times_ms:
        result["avg_ms"] = round(statistics.mean(times_ms), 1)
        result["median_ms"] = round(statistics.median(times_ms), 1)
        result["min_ms"] = round(min(times_ms), 1)
        result["max_ms"] = round(max(times_ms), 1)
        result["pass"] = result["avg_ms"] <= TARGET_MS
    else:
        result["avg_ms"] = 0
        result["median_ms"] = 0
        result["min_ms"] = 0
        result["max_ms"] = 0
        result["pass"] = False

    return result


def main():
    parser = argparse.ArgumentParser(description="AI service performance tester")
    parser.add_argument(
        "--calls", type=int, default=3, help="Number of calls per endpoint (default: 3)"
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{'='*80}")
    print(f"  PERFORMANCE TEST — {args.calls} calls per endpoint (target: {TARGET_MS}ms)")
    print(f"{'='*80}{RESET}\n")

    results = []
    for ep in ENDPOINTS:
        print(f"  Testing {ep['name']} ...", end=" ", flush=True)
        result = run_test(ep, args.calls)
        results.append(result)
        status = f"{GREEN}PASS{RESET}" if result["pass"] else f"{RED}FAIL{RESET}"
        print(f"{result['avg_ms']}ms avg — {status}")

    # Summary table
    print(f"\n{BOLD}{'─'*80}")
    header = (
        f"{'Endpoint':<25} | {'Avg':>8} | {'Median':>8} | {'Min':>8} | "
        f"{'Max':>8} | {'Err':>4} | {'FB':>4} | Result"
    )
    print(header)
    print(f"{'─'*80}{RESET}")

    all_pass = True
    for r in results:
        status = f"{GREEN}PASS{RESET}" if r["pass"] else f"{RED}FAIL{RESET}"
        if not r["pass"]:
            all_pass = False
        print(
            f"{r['name']:<25} | {r['avg_ms']:>7.1f}ms | {r['median_ms']:>7.1f}ms | "
            f"{r['min_ms']:>7.1f}ms | {r['max_ms']:>7.1f}ms | {r['errors']:>4} | "
            f"{r['fallbacks']:>4} | {status}"
        )

    print(f"\n{'─'*80}")
    if all_pass:
        print(f"{GREEN}{BOLD}✅ OVERALL: PASS — All endpoints within {TARGET_MS}ms target{RESET}")
    else:
        print(f"{RED}{BOLD}❌ OVERALL: FAIL — One or more endpoints exceeded {TARGET_MS}ms target{RESET}")
    print()

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
