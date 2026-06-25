"""
Agent 2: Format Validator Agent
Applies rule-based checks on top of Agent 1's structured output:
- Missing unit ID on numeric-with-unit fields
- Whitespace-only values
- Basic type mismatches
"""

import json
import re
import sys
import os

sys.path.append(os.path.dirname(__file__))
from intake_agent import load_test_cases, intake_agent


# Questions we know require a unit ID based on real production errors
# (id 395 = weight, in real mCare this list would come from template metadata)
NUMERIC_WITH_UNIT_QUESTION_IDS = {395, 342, 344, 268, 269}


def is_whitespace_only(value) -> bool:
    return isinstance(value, str) and value.strip() == "" and value != ""


def has_unit_format(value: str) -> bool:
    """Checks for pattern like 20::505 or 40::505::06/08/2026"""
    return bool(re.match(r"^[\d.]+::\d+(::.+)?$", str(value)))


def format_validator_agent(structured: dict) -> list:
    """
    Takes Agent 1's structured output and returns a list of
    format-level issues found.
    """
    issues = []

    for q in structured["answered_questions"]:
        qid = q["id"]
        value = q["value"]

        # Check 1: Whitespace-only value (looks empty but isn't flagged as empty)
        if is_whitespace_only(value):
            issues.append({
                "question_id": qid,
                "issue_type": "whitespace_only_value",
                "original_value": value,
                "description": "Field contains only whitespace, treat as missing"
            })
            continue

        # Check 2: Numeric-with-unit field missing unit format
        if qid in NUMERIC_WITH_UNIT_QUESTION_IDS:
            if not has_unit_format(value):
                issues.append({
                    "question_id": qid,
                    "issue_type": "missing_unit_id",
                    "original_value": value,
                    "description": "Numeric field requires [value]::[unitId] format"
                })

    # Check 3: Empty mandatory-looking fields (flagged by Agent 1 already)
    for qid in structured["empty_question_ids"]:
        issues.append({
            "question_id": qid,
            "issue_type": "missing_mandatory_field",
            "original_value": "",
            "description": "Required field submitted empty"
        })

    return issues


def main():
    test_cases = load_test_cases()

    print("=" * 65)
    print("   AGENT 2: FORMAT VALIDATOR — Test Run")
    print("=" * 65)

    for case in test_cases:
        structured = intake_agent(case["submission"])
        issues = format_validator_agent(structured)

        print(f"\n📋 {case['test_id']}: {case['description']}")
        print("-" * 65)

        if issues:
            for issue in issues:
                print(f"  ⚠️  Q{issue['question_id']}: {issue['issue_type']} "
                      f"— {issue['description']}")
        else:
            print("  ✅ No format issues detected")

        print(f"  Expected classification: {case['expected_classification']}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()