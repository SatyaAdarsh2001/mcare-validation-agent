"""
Agent 1: Intake Agent
Reads a raw mCare submission and extracts a clean, structured
representation for the agents downstream to work with.
"""

import json


def load_test_cases(path="data/test_submissions.json"):
    """Load all test case submissions from our reference JSON file."""
    with open(path, "r") as f:
        data = json.load(f)
    return data["test_cases"]


def intake_agent(submission: dict) -> dict:
    """
    Takes a raw submission dict and returns a structured summary:
    - member/template metadata
    - list of answered questions
    - list of blank/empty questions
    """
    questions = submission.get("QUESTIONS", [])

    answered = []
    empty = []

    for q in questions:
        value = q.get("value", "")
        if value is None or str(value).strip() == "":
            empty.append(q["id"])
        else:
            answered.append({"id": q["id"], "value": value})

    structured = {
        "member_id": submission.get("member_id"),
        "template_id": submission.get("id"),
        "version": submission.get("version"),
        "completion_date": submission.get("completion_date"),
        "total_questions": len(questions),
        "answered_questions": answered,
        "empty_question_ids": empty,
    }

    return structured


def main():
    test_cases = load_test_cases()

    print("=" * 65)
    print("   AGENT 1: INTAKE AGENT — Test Run")
    print("=" * 65)

    for case in test_cases:
        print(f"\n📋 {case['test_id']}: {case['description']}")
        print("-" * 65)

        structured = intake_agent(case["submission"])

        print(f"Member ID: {structured['member_id']}")
        print(f"Template ID: {structured['template_id']} (v{structured['version']})")
        print(f"Total questions in submission: {structured['total_questions']}")
        print(f"Answered: {len(structured['answered_questions'])}")
        print(f"Empty/blank: {structured['empty_question_ids']}")
        print(f"Expected classification: {case['expected_classification']}")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()