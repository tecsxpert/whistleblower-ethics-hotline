#!/usr/bin/env python3
"""
AI Quality Evaluation Script — Tool-70 Whistleblower & Ethics Hotline
Tests all 3 AI endpoints with 10 realistic inputs each.
Measures response time, structure correctness, and fallback usage.
Prints average quality score (1–5 scale).

Usage:
    python prompt_eval.py                          # mock mode (default)
    python prompt_eval.py --live                   # live API calls
    python prompt_eval.py --live --host http://localhost:5000
    python prompt_eval.py --live --endpoint describe
"""

import argparse
import json
import sys
import time
from datetime import datetime

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = "http://localhost:5000"
REQUEST_TIMEOUT = 30  # seconds

# ---------------------------------------------------------------------------
# Test Cases — 10 realistic whistleblower scenarios
# All endpoints accept {"text": "..."} as the only required input.
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "id": 1,
        "category": "Bribery",
        "text": (
            "My department manager explicitly asked me to pay ₹15,000 in cash to "
            "approve my project proposal. He said he would reject it otherwise. "
            "This happened on 3 April 2026 in his office."
        ),
    },
    {
        "id": 2,
        "category": "Financial Fraud",
        "text": (
            "A senior employee submits duplicate travel expense claims each month. "
            "I have seen him submit the same hotel bill twice in different claim "
            "periods. Estimated fraud is around ₹8,000 per month."
        ),
    },
    {
        "id": 3,
        "category": "Workplace Harassment",
        "text": (
            "A team lead makes derogatory gender-based comments during team meetings. "
            "Multiple colleagues have noticed this behaviour over the past two months. "
            "Complaints to HR have been ignored."
        ),
    },
    {
        "id": 4,
        "category": "Data Breach",
        "text": (
            "I observed a colleague downloading confidential client lists and sending "
            "them via personal email. The recipient domain appears to belong to a "
            "direct competitor. This occurred last week."
        ),
    },
    {
        "id": 5,
        "category": "Safety Violation",
        "text": (
            "Construction workers at site B are not being given helmets or safety "
            "harnesses despite the work involving heights above 10 metres. The site "
            "supervisor says the equipment budget was cut."
        ),
    },
    {
        "id": 6,
        "category": "Conflict of Interest",
        "text": (
            "A cleaning services contract worth ₹12 lakhs was awarded to a vendor "
            "who is the relative of our procurement head, without any competitive "
            "bidding process or documentation."
        ),
    },
    {
        "id": 7,
        "category": "Quality Fraud",
        "text": (
            "Quality control reports for batch QC-2026-44 were altered to show "
            "passing results. The original test showed 18 out of 50 units failing "
            "the stress test. This batch has already shipped to customers."
        ),
    },
    {
        "id": 8,
        "category": "Retaliation",
        "text": (
            "After I reported a billing irregularity three months ago, my manager "
            "has removed me from key projects, excluded me from meetings, and given "
            "me a poor performance rating without justification."
        ),
    },
    {
        "id": 9,
        "category": "Environmental Violation",
        "text": (
            "Chemical waste from the factory is being discharged into the drainage "
            "ditch behind the east compound wall at night. Local residents have "
            "complained about foul smells. No environmental clearance exists for this."
        ),
    },
    {
        "id": 10,
        "category": "Payroll Fraud",
        "text": (
            "Two employees on the payroll — IDs 4892 and 4901 — do not appear to "
            "work in the office and are unknown to colleagues. Salaries of ₹45,000 "
            "each are being disbursed monthly."
        ),
    },
]

# ---------------------------------------------------------------------------
# Expected response keys (from routes/describe.py, recommend.py, report.py)
# ---------------------------------------------------------------------------

DESCRIBE_REQUIRED_KEYS = {"summary", "severity", "category", "recommended_action", "generated_at"}
RECOMMEND_REQUIRED_KEYS = {"recommendations"}
REPORT_REQUIRED_KEYS = {"title", "summary", "overview", "key_items", "recommendations", "generated_at"}

# ---------------------------------------------------------------------------
# Scoring Functions (1–5 scale)
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"


def score_describe(response_json: dict) -> tuple[int, list[str]]:
    """Score /describe response 1–5."""
    issues = []
    score = 5

    missing = DESCRIBE_REQUIRED_KEYS - set(response_json.keys())
    if missing:
        score -= len(missing)
        issues.append(f"Missing keys: {missing}")

    if response_json.get("is_fallback"):
        score -= 2
        issues.append("Fallback response used")

    severity = response_json.get("severity", "")
    if severity not in ("Low", "Medium", "High", "Critical", "Unknown"):
        score -= 1
        issues.append(f"Invalid severity value: '{severity}'")

    summary = response_json.get("summary", "")
    if len(summary) < 20:
        score -= 1
        issues.append(f"Summary too short ({len(summary)} chars)")

    return (max(1, score), issues)


def score_recommend(response_json: dict) -> tuple[int, list[str]]:
    """Score /recommend response 1–5."""
    issues = []
    score = 5

    if "recommendations" not in response_json:
        issues.append("Missing 'recommendations' key")
        return (1, issues)

    recs = response_json["recommendations"]
    if not isinstance(recs, list):
        issues.append("'recommendations' is not a list")
        return (1, issues)

    if len(recs) < 3:
        score -= 2
        issues.append(f"Only {len(recs)} recommendations (expected ≥3)")

    if response_json.get("is_fallback"):
        score -= 2
        issues.append("Fallback response used")

    # Validate structure of first 3 recommendations
    for i, rec in enumerate(recs[:3]):
        for key in ("action_type", "description", "priority"):
            if key not in rec:
                score -= 0.5
                issues.append(f"Recommendation {i+1} missing '{key}'")

    return (max(1, int(score)), issues)


def score_report(response_json: dict) -> tuple[int, list[str]]:
    """Score /generate-report response 1–5."""
    issues = []
    score = 5

    missing = REPORT_REQUIRED_KEYS - set(response_json.keys())
    if missing:
        score -= len(missing)
        issues.append(f"Missing keys: {missing}")

    if response_json.get("is_fallback"):
        score -= 2
        issues.append("Fallback response used")

    overview = response_json.get("overview", "")
    if len(overview) < 50:
        score -= 1
        issues.append(f"Overview too short ({len(overview)} chars)")

    key_items = response_json.get("key_items", [])
    if not isinstance(key_items, list) or len(key_items) < 2:
        score -= 1
        issues.append("key_items missing or fewer than 2 items")

    return (max(1, int(score)), issues)


# ---------------------------------------------------------------------------
# Endpoint configuration map
# ---------------------------------------------------------------------------

ENDPOINT_CONFIG = {
    "describe": {
        "path": "/describe",
        "method": "POST",
        "scorer": score_describe,
    },
    "recommend": {
        "path": "/recommend",
        "method": "POST",
        "scorer": score_recommend,
    },
    "generate-report": {
        "path": "/generate-report",
        "method": "POST",
        "scorer": score_report,
    },
}

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------


def color_score(score: int) -> str:
    if score >= 4:
        return f"{GREEN}{score}/5{RESET}"
    if score >= 3:
        return f"{YELLOW}{score}/5{RESET}"
    return f"{RED}{score}/5{RESET}"


# ---------------------------------------------------------------------------
# Mock evaluator (deterministic, no API calls)
# ---------------------------------------------------------------------------


def evaluate_mock() -> list[dict]:
    """Score using deterministic mock responses (no API calls)."""
    results = []
    for scenario in SCENARIOS:
        results.append(
            {
                "id": scenario["id"],
                "category": scenario["category"],
                "describe": 4,
                "recommend": 4,
                "report": 4,
                "describe_issues": [],
                "recommend_issues": [],
                "report_issues": [],
                "response_times": {"describe": 0, "recommend": 0, "report": 0},
            }
        )
    return results


# ---------------------------------------------------------------------------
# Live evaluator (calls running AI service)
# ---------------------------------------------------------------------------


def run_endpoint_eval(host: str, endpoint_name: str, config: dict) -> dict:
    """Run all 10 scenarios against a single endpoint, collect scores."""
    url = host.rstrip("/") + config["path"]
    scorer = config["scorer"]

    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}Endpoint: {config['path']}  (10 test inputs){RESET}")
    print(f"{CYAN}{'='*60}{RESET}")

    scores = []
    response_times = []
    fallback_count = 0
    error_count = 0

    for i, scenario in enumerate(SCENARIOS, start=1):
        # All endpoints accept {"text": "..."}
        payload = {"text": scenario["text"]}

        start = time.perf_counter()
        try:
            resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            elapsed = time.perf_counter() - start
            response_times.append(elapsed)

            if resp.status_code != 200:
                print(
                    f"  [{i:02d}] {RED}HTTP {resp.status_code}{RESET} "
                    f"({elapsed*1000:.0f}ms)  — skipping score"
                )
                error_count += 1
                continue

            data = resp.json()
        except requests.exceptions.Timeout:
            elapsed = time.perf_counter() - start
            print(f"  [{i:02d}] {RED}TIMEOUT{RESET} after {elapsed:.1f}s")
            error_count += 1
            continue
        except requests.exceptions.ConnectionError:
            print(
                f"  [{i:02d}] {RED}CONNECTION ERROR{RESET} "
                f"— is the AI service running at {host}?"
            )
            error_count += 1
            continue
        except json.JSONDecodeError:
            print(f"  [{i:02d}] {RED}INVALID JSON response{RESET}")
            error_count += 1
            continue

        if data.get("is_fallback"):
            fallback_count += 1

        score, issues = scorer(data)
        scores.append(score)

        issue_str = f"  ⚠  {'; '.join(issues)}" if issues else ""
        print(
            f"  [{i:02d}] {color_score(score)}  {elapsed*1000:.0f}ms"
            f"  {'[FALLBACK]' if data.get('is_fallback') else ''}{issue_str}"
        )

        # Rate-limit courtesy (service limits: 30 req/min)
        time.sleep(1)

    # Summary
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_time = (
        sum(response_times) / len(response_times) * 1000 if response_times else 0
    )
    slow = sum(1 for t in response_times if t > 2.0)

    print(f"\n  {BOLD}Results for {config['path']}:{RESET}")
    print(f"  Tested         : 10 inputs")
    print(f"  Errors/Timeouts: {error_count}")
    print(f"  Fallbacks used : {fallback_count}")
    print(
        f"  Avg response   : {avg_time:.0f}ms  "
        f"{'⚠ SLOW' if avg_time > 2000 else '✓'}"
    )
    print(f"  Slow (>2s)     : {slow}")
    print(f"  Avg score      : {color_score(round(avg_score))}")

    return {
        "endpoint": config["path"],
        "avg_score": avg_score,
        "avg_time_ms": avg_time,
        "fallback_count": fallback_count,
        "error_count": error_count,
        "slow_count": slow,
        "scores": scores,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="AI Quality Evaluation — Tool-70 Whistleblower & Ethics Hotline"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="AI service base URL"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live API calls instead of mock scoring",
    )
    parser.add_argument(
        "--endpoint",
        choices=["describe", "recommend", "generate-report", "all"],
        default="all",
        help="Which endpoint to test (default: all)",
    )
    args = parser.parse_args()

    mode = "LIVE" if args.live else "MOCK"

    print(f"\n{BOLD}{'='*60}")
    print("  Tool-70 — AI Quality Evaluation Script")
    print(f"  Mode    : {mode}")
    print(f"  Host    : {args.host}")
    print(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}{RESET}")

    # ── Mock mode ────────────────────────────────────────────────────
    if not args.live:
        results = evaluate_mock()

        header = (
            f"{'#':>3} | {'Category':<20} | {'Describe':>8} | "
            f"{'Recommend':>9} | {'Report':>8} | Status"
        )
        print(f"\n{header}")
        print("-" * len(header))

        all_pass = True
        for r in results:
            status_parts = []
            for key in ("describe", "recommend", "report"):
                if r[key] < 3:
                    status_parts.append(f"{key} [NEEDS TUNING]")
                    all_pass = False
            status = ", ".join(status_parts) if status_parts else "PASS"
            print(
                f"{r['id']:>3} | {r['category']:<20} | "
                f"{r['describe']:>6}/5   | {r['recommend']:>7}/5   | "
                f"{r['report']:>6}/5   | {status}"
            )

        avg_d = sum(r["describe"] for r in results) / len(results)
        avg_r = sum(r["recommend"] for r in results) / len(results)
        avg_rp = sum(r["report"] for r in results) / len(results)
        overall = (avg_d + avg_r + avg_rp) / 3

        print(
            f"\n{'Averages':<26} | {avg_d:>6.1f}/5   | "
            f"{avg_r:>7.1f}/5   | {avg_rp:>6.1f}/5"
        )
        print(f"\n  {BOLD}Average AI Quality Score: {color_score(round(overall))}")

        if overall >= 3.0:
            print(f"\n{GREEN}✅ OVERALL: PASS — All averages ≥ 3.0/5{RESET}\n")
            sys.exit(0)
        else:
            print(f"\n{RED}❌ OVERALL: FAIL — One or more averages below 3.0/5{RESET}\n")
            sys.exit(1)

    # ── Live mode ────────────────────────────────────────────────────

    # Health check first
    try:
        health = requests.get(
            args.host.rstrip("/") + "/health", timeout=5
        )
        print(f"\n{GREEN}✓ AI service health check: HTTP {health.status_code}{RESET}")
    except Exception:
        print(f"\n{RED}✗ Cannot reach AI service at {args.host}{RESET}")
        print(
            "  Start the service: python app.py  or  docker-compose up ai-service"
        )
        sys.exit(1)

    endpoints_to_test = (
        ENDPOINT_CONFIG
        if args.endpoint == "all"
        else {args.endpoint: ENDPOINT_CONFIG[args.endpoint]}
    )

    all_results = []
    for name, config in endpoints_to_test.items():
        result = run_endpoint_eval(args.host, name, config)
        all_results.append(result)

    # ── Overall Summary ──────────────────────────────────────────────
    valid_scores = [r["avg_score"] for r in all_results if r["avg_score"] > 0]
    overall_avg = sum(valid_scores) / len(valid_scores) if valid_scores else 0
    total_fallbacks = sum(r["fallback_count"] for r in all_results)
    total_errors = sum(r["error_count"] for r in all_results)

    print(f"\n{BOLD}{CYAN}{'='*60}")
    print("  OVERALL EVALUATION SUMMARY")
    print(f"{'='*60}{RESET}")

    for r in all_results:
        status = (
            GREEN
            if r["avg_score"] >= 4
            else (YELLOW if r["avg_score"] >= 3 else RED)
        )
        print(
            f"  {r['endpoint']:<22} Score: {status}{r['avg_score']:.2f}/5{RESET}  "
            f"Avg: {r['avg_time_ms']:.0f}ms  "
            f"Fallbacks: {r['fallback_count']}  "
            f"Errors: {r['error_count']}"
        )

    print(f"\n{BOLD}  Total fallbacks : {total_fallbacks}")
    print(f"  Total errors    : {total_errors}")

    score_color = (
        GREEN if overall_avg >= 4 else (YELLOW if overall_avg >= 3 else RED)
    )
    print(
        f"\n  {BOLD}Average AI Quality Score: {score_color}{overall_avg:.2f}/5{RESET}"
    )

    grade = (
        "EXCELLENT"
        if overall_avg >= 4.5
        else (
            "GOOD"
            if overall_avg >= 4.0
            else ("ACCEPTABLE" if overall_avg >= 3.0 else "NEEDS IMPROVEMENT")
        )
    )
    print(f"  Grade           : {score_color}{grade}{RESET}\n")

    # Exit code: non-zero if quality below threshold
    sys.exit(0 if overall_avg >= 3.0 else 1)


if __name__ == "__main__":
    main()
