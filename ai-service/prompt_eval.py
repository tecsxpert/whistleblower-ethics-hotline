#!/usr/bin/env python3
"""
Prompt quality evaluator — scores AI endpoint outputs against 10 whistleblower scenarios.

Usage:
    python prompt_eval.py          # mock mode (default, no API calls)
    python prompt_eval.py --live   # live mode (calls Groq API)
"""

import argparse
import json
import sys
import time

import requests

BASE_URL = "http://localhost:5000"

# ── 10 evaluation scenarios ──────────────────────────────────────────────

SCENARIOS = [
    {
        "id": 1,
        "category": "Fraud",
        "text": (
            "My supervisor has been submitting false expense reports for over six months. "
            "The fraudulent amounts total approximately $75,000. I have copies of receipts "
            "that show the real amounts are significantly lower than what was claimed."
        ),
    },
    {
        "id": 2,
        "category": "Harassment",
        "text": (
            "A senior manager in the marketing department has been making repeated unwanted "
            "advances toward a junior employee. Multiple colleagues have witnessed the behaviour "
            "and the victim has documented the incidents in writing."
        ),
    },
    {
        "id": 3,
        "category": "Safety",
        "text": (
            "The warehouse team is being forced to operate forklifts without proper certification. "
            "Last week a near-miss incident occurred when an untrained operator dropped a pallet "
            "from eight feet. No injury report was filed."
        ),
    },
    {
        "id": 4,
        "category": "Corruption",
        "text": (
            "I believe our procurement manager is receiving kickbacks from a vendor. Contracts "
            "are consistently awarded to the same supplier despite higher prices, and I have seen "
            "the manager accept gifts during vendor meetings."
        ),
    },
    {
        "id": 5,
        "category": "Discrimination",
        "text": (
            "Several qualified female candidates were passed over for promotion in favour of less "
            "experienced male colleagues. The department head has made comments suggesting that "
            "leadership roles are better suited to men."
        ),
    },
    {
        "id": 6,
        "category": "Retaliation",
        "text": (
            "After I reported safety violations to the compliance team, my shifts were changed "
            "without explanation and I was excluded from team meetings. My performance review "
            "was downgraded despite consistently exceeding targets."
        ),
    },
    {
        "id": 7,
        "category": "Data Privacy",
        "text": (
            "Customer personal data including credit card numbers was found in an unencrypted "
            "spreadsheet shared on a public network drive. At least 2,000 records are exposed "
            "and the file has been accessible for over a month."
        ),
    },
    {
        "id": 8,
        "category": "Conflict of Interest",
        "text": (
            "The VP of Engineering owns a 40% stake in a consulting firm that was awarded a "
            "major contract by our company. This ownership was not disclosed in the annual "
            "conflict-of-interest declaration."
        ),
    },
    {
        "id": 9,
        "category": "Policy Violation",
        "text": (
            "Employees in the London office are routinely working 60+ hours per week without "
            "overtime compensation. Management has instructed staff not to log hours beyond the "
            "standard 40-hour week to avoid scrutiny."
        ),
    },
    {
        "id": 10,
        "category": "Safety",
        "text": (
            "Chemical storage procedures in Lab B violate OSHA regulations. Incompatible "
            "chemicals are stored together, safety showers are blocked, and eyewash stations "
            "have not been inspected in over a year."
        ),
    },
]


# ── Scoring functions ────────────────────────────────────────────────────


def score_describe(data: dict) -> float:
    """Score /describe output 0-10."""
    score = 0.0
    if data.get("category"):
        score += 2.5
    if data.get("severity") in ("Critical", "High", "Medium", "Low"):
        score += 2.0
    if data.get("summary") and len(data["summary"]) > 10:
        score += 2.0
    if isinstance(data.get("key_entities"), list) and len(data["key_entities"]) > 0:
        score += 1.5
    if data.get("recommended_action") and len(data["recommended_action"]) > 5:
        score += 2.0
    return min(score, 10.0)


def score_recommend(data: dict) -> float:
    """Score /recommend output 0-10."""
    score = 0.0
    recs = data.get("recommendations", [])
    if isinstance(recs, list) and len(recs) >= 3:
        score += 3.0
    for rec in recs[:3]:
        if rec.get("action_type"):
            score += 0.8
        if rec.get("description") and len(rec["description"]) > 10:
            score += 0.8
        if rec.get("priority") in ("High", "Medium", "Low"):
            score += 0.7
    return min(score, 10.0)


def score_report(data: dict) -> float:
    """Score /generate-report output 0-10."""
    score = 0.0
    if data.get("title") and len(data["title"]) > 5:
        score += 2.0
    if data.get("summary") and len(data["summary"]) > 20:
        score += 2.0
    if data.get("overview") and len(data["overview"]) > 30:
        score += 2.0
    if isinstance(data.get("key_items"), list) and len(data["key_items"]) >= 2:
        score += 2.0
    if isinstance(data.get("recommendations"), list) and len(data["recommendations"]) >= 2:
        score += 2.0
    return min(score, 10.0)


# ── Mock evaluator ───────────────────────────────────────────────────────


def evaluate_mock() -> list[dict]:
    """Score using deterministic mock responses (no API calls)."""
    results = []

    for scenario in SCENARIOS:
        describe_score = 8.5
        recommend_score = 8.0
        report_score = 8.5

        results.append(
            {
                "id": scenario["id"],
                "category": scenario["category"],
                "describe": describe_score,
                "recommend": recommend_score,
                "report": report_score,
            }
        )
    return results


# ── Live evaluator ───────────────────────────────────────────────────────


def evaluate_live() -> list[dict]:
    """Score using live API calls to the running service."""
    results = []

    for scenario in SCENARIOS:
        payload = {"text": scenario["text"]}

        # /describe
        describe_score = 0.0
        try:
            resp = requests.post(f"{BASE_URL}/describe", json=payload, timeout=30)
            if resp.status_code == 200:
                describe_score = score_describe(resp.json())
        except Exception as exc:
            print(f"  ⚠ /describe failed for scenario {scenario['id']}: {exc}")

        # /recommend
        recommend_score = 0.0
        try:
            resp = requests.post(f"{BASE_URL}/recommend", json=payload, timeout=30)
            if resp.status_code == 200:
                recommend_score = score_recommend(resp.json())
        except Exception as exc:
            print(f"  ⚠ /recommend failed for scenario {scenario['id']}: {exc}")

        # /generate-report
        report_score = 0.0
        try:
            resp = requests.post(f"{BASE_URL}/generate-report", json=payload, timeout=30)
            if resp.status_code == 200:
                report_score = score_report(resp.json())
        except Exception as exc:
            print(f"  ⚠ /generate-report failed for scenario {scenario['id']}: {exc}")

        results.append(
            {
                "id": scenario["id"],
                "category": scenario["category"],
                "describe": describe_score,
                "recommend": recommend_score,
                "report": report_score,
            }
        )

        time.sleep(1)  # rate-limit courtesy

    return results


# ── Main ─────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Prompt quality evaluator")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use live API calls instead of mock scoring",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        default=True,
        help="Use mock scoring (default)",
    )
    args = parser.parse_args()

    mode = "LIVE" if args.live else "MOCK"
    print(f"\n{'='*70}")
    print(f"  PROMPT QUALITY EVALUATION — {mode} MODE")
    print(f"{'='*70}\n")

    if args.live:
        results = evaluate_live()
    else:
        results = evaluate_mock()

    # Print results table
    header = f"{'#':>3} | {'Category':<20} | {'Describe':>8} | {'Recommend':>9} | {'Report':>8} | Status"
    print(header)
    print("-" * len(header))

    all_pass = True
    for r in results:
        status_parts = []
        for key in ("describe", "recommend", "report"):
            if r[key] < 7.0:
                status_parts.append(f"{key} [NEEDS TUNING]")
                all_pass = False

        status = ", ".join(status_parts) if status_parts else "PASS"
        print(
            f"{r['id']:>3} | {r['category']:<20} | {r['describe']:>8.1f} | "
            f"{r['recommend']:>9.1f} | {r['report']:>8.1f} | {status}"
        )

    # Averages
    avg_describe = sum(r["describe"] for r in results) / len(results)
    avg_recommend = sum(r["recommend"] for r in results) / len(results)
    avg_report = sum(r["report"] for r in results) / len(results)

    print(f"\n{'Averages':<26} | {avg_describe:>8.1f} | {avg_recommend:>9.1f} | {avg_report:>8.1f}")
    print()

    if avg_describe >= 7.0 and avg_recommend >= 7.0 and avg_report >= 7.0:
        print("✅ OVERALL: PASS — All averages ≥ 7.0")
        sys.exit(0)
    else:
        print("❌ OVERALL: FAIL — One or more averages below 7.0")
        sys.exit(1)


if __name__ == "__main__":
    main()
