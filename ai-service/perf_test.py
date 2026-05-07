#!/usr/bin/env python3
"""
Performance Test Script — Tool-70 Whistleblower & Ethics Hotline
Sends concurrent requests per endpoint and reports timing statistics.

Usage:
    python perf_test.py                              # 20 concurrent, all endpoints
    python perf_test.py --host http://localhost:5000
    python perf_test.py --concurrency 20 --endpoint describe
    python perf_test.py --calls 3                    # sequential mode (3 calls each)

Requirements:
    pip install requests
"""

import argparse
import json
import sys
import time
import threading
from datetime import datetime
from statistics import mean, median, stdev

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = "http://localhost:5000"
DEFAULT_CONCURRENCY = 20
REQUEST_TIMEOUT = 30  # seconds
TARGET_MS = 2000  # target response time in ms

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"

# ---------------------------------------------------------------------------
# Test Payloads — all endpoints accept {"text": "..."}
# ---------------------------------------------------------------------------

PAYLOADS = {
    "/describe": {
        "text": (
            "My direct manager asked me to pay ₹10,000 in cash to approve my "
            "budget request. He implied that without this payment the request "
            "would be indefinitely delayed."
        ),
    },
    "/recommend": {
        "text": (
            "An employee is submitting duplicate expense claims each month. "
            "Approximately ₹12,000 per month has been fraudulently claimed "
            "over the past six months."
        ),
    },
    "/generate-report": {
        "text": (
            "Multiple employees have reported persistent workplace harassment "
            "by a department head including verbal abuse, intimidation tactics, "
            "and gender-based discriminatory remarks during team meetings."
        ),
    },
}

# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------


class RequestResult:
    __slots__ = ("endpoint", "status_code", "elapsed_ms", "is_fallback", "error")

    def __init__(self, endpoint, status_code=None, elapsed_ms=None,
                 is_fallback=False, error=None):
        self.endpoint = endpoint
        self.status_code = status_code
        self.elapsed_ms = elapsed_ms
        self.is_fallback = is_fallback
        self.error = error


def make_request(host: str, path: str, payload: dict,
                 results: list, lock: threading.Lock):
    """Send a single POST request and record the result."""
    url = host.rstrip("/") + path
    start = time.perf_counter()
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        elapsed_ms = (time.perf_counter() - start) * 1000

        is_fallback = False
        if resp.headers.get("Content-Type", "").startswith("application/json"):
            try:
                data = resp.json()
                is_fallback = data.get("is_fallback", False)
            except json.JSONDecodeError:
                pass

        result = RequestResult(
            endpoint=path,
            status_code=resp.status_code,
            elapsed_ms=elapsed_ms,
            is_fallback=is_fallback,
        )
    except requests.exceptions.Timeout:
        elapsed_ms = (time.perf_counter() - start) * 1000
        result = RequestResult(
            endpoint=path, elapsed_ms=elapsed_ms, error="TIMEOUT"
        )
    except requests.exceptions.ConnectionError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        result = RequestResult(
            endpoint=path, elapsed_ms=elapsed_ms,
            error=f"CONNECTION_ERROR: {e}"
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        result = RequestResult(
            endpoint=path, elapsed_ms=elapsed_ms, error=str(e)
        )

    with lock:
        results.append(result)


# ---------------------------------------------------------------------------
# Sequential runner (legacy mode)
# ---------------------------------------------------------------------------


def run_sequential_test(host: str, path: str, payload: dict,
                        num_calls: int) -> list:
    """Run N sequential calls and return results (for low-concurrency tests)."""
    results = []
    lock = threading.Lock()
    wall_start = time.perf_counter()

    for i in range(num_calls):
        make_request(host, path, payload, results, lock)
        if i < num_calls - 1:
            time.sleep(0.5)  # avoid rate limiting

    wall_time = (time.perf_counter() - wall_start) * 1000
    return results, wall_time


# ---------------------------------------------------------------------------
# Concurrent runner
# ---------------------------------------------------------------------------


def run_concurrent_test(host: str, path: str, payload: dict,
                        concurrency: int) -> tuple[list, float]:
    """Send N concurrent requests and return results + wall time."""
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}Endpoint : {path}{RESET}")
    print(f"Requests : {concurrency} concurrent")
    print(f"{CYAN}{'='*60}{RESET}")

    results = []
    lock = threading.Lock()
    threads = []

    wall_start = time.perf_counter()

    for _ in range(concurrency):
        t = threading.Thread(
            target=make_request,
            args=(host, path, payload, results, lock),
            daemon=True,
        )
        threads.append(t)

    # Launch all threads simultaneously
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    wall_time = (time.perf_counter() - wall_start) * 1000
    return results, wall_time


# ---------------------------------------------------------------------------
# Results printer
# ---------------------------------------------------------------------------


def print_results(results: list, wall_time: float) -> dict:
    """Analyse and print performance results. Returns summary dict."""
    successful = [r for r in results if r.status_code == 200]
    errors = [r for r in results if r.error]
    non_200 = [r for r in results if r.status_code and r.status_code != 200]
    fallbacks = [r for r in results if r.is_fallback]
    slow = [r for r in results if r.elapsed_ms and r.elapsed_ms > 2000]

    success_rate = len(successful) / len(results) * 100 if results else 0

    times = [r.elapsed_ms for r in results if r.elapsed_ms is not None]
    avg_ms = mean(times) if times else 0
    med_ms = median(times) if times else 0
    min_ms = min(times) if times else 0
    max_ms = max(times) if times else 0
    std_ms = stdev(times) if len(times) > 1 else 0

    # ASCII histogram
    buckets = [0] * 6  # <500, 500-1k, 1-1.5k, 1.5-2k, 2-3k, >3k
    for t in times:
        if t < 500:
            buckets[0] += 1
        elif t < 1000:
            buckets[1] += 1
        elif t < 1500:
            buckets[2] += 1
        elif t < 2000:
            buckets[3] += 1
        elif t < 3000:
            buckets[4] += 1
        else:
            buckets[5] += 1
    labels = ["<500ms", "500-1s", "1-1.5s", "1.5-2s", "2-3s", ">3s"]

    print(f"\n  {BOLD}Response Time Distribution:{RESET}")
    max_bucket = max(buckets) if buckets else 1
    for label, count in zip(labels, buckets):
        bar_len = int(count / max_bucket * 30) if max_bucket else 0
        bar = "█" * bar_len
        color = (
            RED if label in (">3s", "2-3s")
            else (YELLOW if label == "1.5-2s" else GREEN)
        )
        print(f"  {label:>8}  {color}{bar:<30}{RESET}  {count}")

    # Summary table
    sr_color = GREEN if success_rate >= 95 else (YELLOW if success_rate >= 80 else RED)
    avg_color = GREEN if avg_ms < 1500 else (YELLOW if avg_ms < 2000 else RED)

    print(f"\n  {BOLD}Performance Summary:{RESET}")
    print(f"  Total requests   : {len(results)}")
    print(
        f"  Successful (200) : {sr_color}{len(successful)} "
        f"({success_rate:.1f}%){RESET}"
    )
    print(f"  Errors/Timeouts  : {RED if errors else GREEN}{len(errors)}{RESET}")
    print(f"  Non-200 HTTP     : {len(non_200)}")
    print(f"  Fallbacks        : {len(fallbacks)}")
    print(f"  Slow (>2s)       : {RED if slow else GREEN}{len(slow)}{RESET}")
    print(f"  Wall clock time  : {wall_time:.0f}ms")
    print(f"\n  {BOLD}Latency (ms):{RESET}")
    print(f"  Avg   : {avg_color}{avg_ms:.0f}ms{RESET}")
    print(f"  Median: {med_ms:.0f}ms")
    print(f"  Min   : {min_ms:.0f}ms")
    print(f"  Max   : {max_ms:.0f}ms")
    print(f"  StdDev: {std_ms:.0f}ms")

    if slow:
        print(f"\n  {YELLOW}⚠  Slow request details:{RESET}")
        for r in slow:
            print(
                f"     {r.endpoint}  {r.elapsed_ms:.0f}ms  "
                f"{'[FALLBACK]' if r.is_fallback else ''}"
                f"{'['+r.error+']' if r.error else ''}"
            )

    return {
        "total": len(results),
        "success": len(successful),
        "success_rate": success_rate,
        "avg_ms": avg_ms,
        "med_ms": med_ms,
        "min_ms": min_ms,
        "max_ms": max_ms,
        "slow_count": len(slow),
        "error_count": len(errors),
        "fallback_count": len(fallbacks),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="AI Performance Test — Tool-70 Whistleblower & Ethics Hotline"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="AI service base URL"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help="Number of concurrent requests per endpoint (default: 20)",
    )
    parser.add_argument(
        "--calls",
        type=int,
        default=0,
        help="If set, run N sequential calls instead of concurrent mode",
    )
    parser.add_argument(
        "--endpoint",
        choices=["describe", "recommend", "generate-report"],
        help="Single endpoint to test (default: all)",
    )
    args = parser.parse_args()

    is_sequential = args.calls > 0

    print(f"\n{BOLD}{'='*60}")
    print("  Tool-70 — AI Service Performance Test")
    print(f"  Host        : {args.host}")
    if is_sequential:
        print(f"  Mode        : Sequential ({args.calls} calls/endpoint)")
    else:
        print(f"  Concurrency : {args.concurrency} threads/endpoint")
    print(f"  Target      : <{TARGET_MS}ms avg, >95% success")
    print(f"  Started     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{RESET}")

    # Health check
    try:
        health = requests.get(
            args.host.rstrip("/") + "/health", timeout=5
        )
        print(f"\n{GREEN}✓ AI service health: HTTP {health.status_code}{RESET}")
    except Exception:
        print(f"\n{RED}✗ Cannot reach AI service at {args.host}{RESET}")
        print(
            "  Start the service: python app.py  or  docker-compose up ai-service"
        )
        sys.exit(1)

    endpoints_to_test = (
        {f"/{args.endpoint}": PAYLOADS[f"/{args.endpoint}"]}
        if args.endpoint
        else PAYLOADS
    )

    all_summaries = []
    all_slow = []

    for path, payload in endpoints_to_test.items():
        if is_sequential:
            results, wall_time = run_sequential_test(
                args.host, path, payload, args.calls
            )
            print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
            print(f"{BOLD}Endpoint : {path}{RESET}")
            print(f"Requests : {args.calls} sequential")
            print(f"{CYAN}{'='*60}{RESET}")
        else:
            results, wall_time = run_concurrent_test(
                args.host, path, payload, args.concurrency
            )

        summary = print_results(results, wall_time)
        summary["endpoint"] = path
        all_summaries.append(summary)
        if summary["slow_count"] > 0:
            all_slow.append(path)

    # ── Final Report ─────────────────────────────────────────────────
    overall_avg = mean(s["avg_ms"] for s in all_summaries)
    overall_success = mean(s["success_rate"] for s in all_summaries)
    total_errors = sum(s["error_count"] for s in all_summaries)

    print(f"\n{BOLD}{CYAN}{'='*60}")
    print("  FINAL PERFORMANCE REPORT")
    print(f"{'='*60}{RESET}")

    for s in all_summaries:
        avg_color = (
            GREEN if s["avg_ms"] < 1500
            else (YELLOW if s["avg_ms"] < 2000 else RED)
        )
        sr_color = GREEN if s["success_rate"] >= 95 else RED
        print(
            f"  {s['endpoint']:<22}"
            f"  Avg: {avg_color}{s['avg_ms']:.0f}ms{RESET}"
            f"  Success: {sr_color}{s['success_rate']:.0f}%{RESET}"
            f"  Slow: {s['slow_count']}"
        )

    print(f"\n  {BOLD}Overall avg response : {overall_avg:.0f}ms{RESET}")
    print(f"  Overall success rate : {overall_success:.1f}%")
    print(f"  Total errors         : {total_errors}")

    if all_slow:
        print(f"\n  {YELLOW}⚠  Slow endpoints (>2s avg):{RESET}")
        for ep in all_slow:
            print(f"     {ep}")
    else:
        print(f"\n  {GREEN}✓ All endpoints within 2s target{RESET}")

    passed = overall_avg < TARGET_MS and overall_success >= 95
    status = GREEN if passed else RED
    verdict = "PASS" if passed else "NEEDS REVIEW"
    print(f"\n  {BOLD}Performance Status: {status}{verdict}{RESET}\n")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
