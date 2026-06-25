"""
Agent 5: Report Agent
Combines the outputs of Agents 1-4 into a single, structured
validation report - matching the "errors + corrected data" output
format defined in our Week 1 design document.

This is the final artifact that would be returned to mCare's .NET
backend via the REST API, and used for audit trail purposes.
"""

import sys
import os
import json

sys.path.append(os.path.dirname(__file__))
from intake_agent import load_test_cases, intake_agent
from format_validator_agent import format_validator_agent
from correction_agent import correction_agent


def report_agent(case: dict, structured: dict, format_issues: list,
                  classification: str, corrections: list) -> dict:
    """
    Builds the final validation report for a single submission.
    """

    auto_fixed = [c for c in corrections if c["action"] == "auto_fix"]
    needs_review = [c for c in corrections if c["action"] == "suggest"]

    # Build the corrected_data dict - only includes auto-fixed values
    corrected_data = {
        str(c["question_id"]): c["corrected_value"]
        for c in auto_fixed
    }

    if classification == "USER_ERROR":
        if needs_review:
            status = "needs_review"
        elif auto_fixed:
            status = "auto_corrected"
        else:
            status = "clean"
    elif classification in ("TEMPLATE_ISSUE", "SYSTEM_ISSUE"):
        status = "escalated"
    else:
        status = "unknown"

    report = {
        "submission_id": case["test_id"],
        "member_id": structured["member_id"],
        "template_id": structured["template_id"],
        "version": structured["version"],
        "status": status,
        "classification": classification,
        "issues": format_issues,
        "corrected_data": corrected_data,
        "auto_fixed": [c["question_id"] for c in auto_fixed],
        "needs_review": [
            {"question_id": c["question_id"], "suggestion": c["suggestion"]}
            for c in needs_review
        ],
        "escalation": {
            "required": classification in ("TEMPLATE_ISSUE", "SYSTEM_ISSUE"),
            "route_to": (
                "Template/Development Team" if classification == "TEMPLATE_ISSUE"
                else "Infrastructure/DBA Team" if classification == "SYSTEM_ISSUE"
                else None
            )
        },
        "original_cca_error": case["known_error"]
    }

    return report


def print_report(report: dict):
    print(f"\n📋 Submission: {report['submission_id']} "
          f"(Member: {report['member_id']}, Template: {report['template_id']})")
    print("-" * 65)
    print(f"  Status:         {report['status'].upper()}")
    print(f"  Classification: {report['classification']}")

    if report["issues"]:
        print(f"  Issues found:   {len(report['issues'])}")
        for issue in report["issues"]:
            print(f"    - Q{issue['question_id']}: {issue['issue_type']}")

    if report["corrected_data"]:
        print(f"  Auto-corrected: {report['corrected_data']}")

    if report["needs_review"]:
        print(f"  Needs review:")
        for item in report["needs_review"]:
            print(f"    - Q{item['question_id']}: {item['suggestion']}")

    if report["escalation"]["required"]:
        print(f"  ⚠️  ESCALATED to: {report['escalation']['route_to']}")

    print(f"  Original CCA error: \"{report['original_cca_error'][:80]}...\"")


def main():
    test_cases = load_test_cases()

    print("=" * 65)
    print("   AGENT 5: REPORT AGENT — Full Pipeline Test Run")
    print("=" * 65)

    all_reports = []

    for case in test_cases:
        structured = intake_agent(case["submission"])
        format_issues = format_validator_agent(structured)
        classification = case["expected_classification"]  # known label for this test
        corrections = correction_agent(structured, format_issues, classification)

        report = report_agent(case, structured, format_issues, classification, corrections)
        print_report(report)
        all_reports.append(report)

    print("\n" + "=" * 65)
    print("   SUMMARY")
    print("=" * 65)

    status_counts = {}
    for r in all_reports:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    for status, count in status_counts.items():
        print(f"  {status}: {count}")

    # Save full reports to a file for inspection
    output_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "validation_reports.json")
    with open(output_path, "w") as f:
        json.dump(all_reports, f, indent=2)
    print(f"\n  📁 Full reports saved to: data/validation_reports.json")

    print("=" * 65)


if __name__ == "__main__":
    main()