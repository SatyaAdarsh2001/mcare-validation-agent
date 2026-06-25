"""
Agent 3: Classifier Agent
Uses Azure OpenAI to classify each submission as:
- USER_ERROR     (Care Manager data-entry mistake, fixable)
- TEMPLATE_ISSUE  (Template/config mismatch, needs dev team)
- SYSTEM_ISSUE    (Infrastructure/session problem, needs infra team)

Falls back to rule-based hints from Agent 2's findings when possible,
and uses AI reasoning for ambiguous cases.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))
from intake_agent import load_test_cases, intake_agent
from format_validator_agent import format_validator_agent

load_dotenv()

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_KEY")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")


def classifier_agent(structured: dict, format_issues: list, known_error: str) -> dict:
    """
    Determines USER_ERROR vs TEMPLATE_ISSUE vs SYSTEM_ISSUE
    using the structured data, any format issues found, and the
    raw error message returned by CCA.
    """

    prompt = f"""
    You are analyzing an mCare-to-CCA assessment submission error.

    Submission summary:
    - Member ID: {structured['member_id']}
    - Template ID: {structured['template_id']} (v{structured['version']})
    - Total questions: {structured['total_questions']}
    - Empty fields: {structured['empty_question_ids']}

    Format issues found by rule-based validator: {json.dumps(format_issues)}

    Raw error message from CCA: "{known_error}"

    Classify this error into EXACTLY ONE of these three categories:

    1. USER_ERROR - Care Manager data-entry mistake (missing fields,
       wrong format, missing units, whitespace instead of value).
       These are fixable by suggesting or auto-correcting values.

    2. TEMPLATE_ISSUE - Template/configuration problem (invalid
       question ID not in template, answer count mismatch with
       template definition). These need the Template/Development
       team, not a data fix.

    3. SYSTEM_ISSUE - Infrastructure/system problem (database
       timeout, invalid/expired session, network failure). These
       are completely unrelated to the submitted data and need the
       Infrastructure/DBA team.

    Respond ONLY in this exact JSON format, no other text:
    {{
      "classification": "USER_ERROR" or "TEMPLATE_ISSUE" or "SYSTEM_ISSUE",
      "confidence": "high" or "medium" or "low",
      "reasoning": "brief one-sentence explanation"
    }}
    """

    url = f"{ENDPOINT}openai/deployments/{DEPLOYMENT}/chat/completions?api-version=2024-10-21"

    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY
    }

    body = {
        "messages": [
            {
                "role": "system",
                "content": "You are an expert at classifying healthcare "
                            "assessment submission errors. Respond only "
                            "with valid JSON, no markdown formatting."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    result = response.json()

    raw_text = result["choices"][0]["message"]["content"].strip()

    # Clean up in case the model wraps it in markdown fences
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "classification": "UNKNOWN",
            "confidence": "low",
            "reasoning": f"Could not parse AI response: {raw_text}"
        }


def main():
    test_cases = load_test_cases()

    print("=" * 65)
    print("   AGENT 3: CLASSIFIER AGENT — Test Run")
    print("=" * 65)

    correct = 0
    total = len(test_cases)

    for case in test_cases:
        structured = intake_agent(case["submission"])
        format_issues = format_validator_agent(structured)

        result = classifier_agent(
            structured,
            format_issues,
            case["known_error"]
        )

        print(f"\n📋 {case['test_id']}: {case['description']}")
        print("-" * 65)
        print(f"  AI Classification: {result['classification']} "
              f"(confidence: {result['confidence']})")
        print(f"  Reasoning: {result['reasoning']}")
        print(f"  Expected:  {case['expected_classification']}")

        if result["classification"] == case["expected_classification"]:
            print("  ✅ MATCH")
            correct += 1
        else:
            print("  ❌ MISMATCH")

    print("\n" + "=" * 65)
    print(f"   ACCURACY: {correct}/{total} test cases classified correctly")
    print("=" * 65)


if __name__ == "__main__":
    main()