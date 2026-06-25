"""
Agent 4: AI Correction Agent
For submissions classified as USER_ERROR, this agent applies a
two-tier correction strategy:

Tier 1 - Simple format fixes (deterministic, high confidence):
         - Missing unit ID -> auto-append correct unit
         - Whitespace-only value -> treat as missing, prompt for input

Tier 2 - Context-aware suggestions (AI-powered, needs confirmation):
         - Missing mandatory fields where the correct value isn't
           obvious from format alone -> AI suggests based on context
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

# Known unit IDs for specific questions (in real mCare this would come
# from template/concept metadata - hardcoded here for our 7 reference cases)
KNOWN_UNIT_IDS = {
    395: "505",  # Weight in Pounds
    342: "366",  # observed in TC003 data (already correctly formatted)
    344: "506",  # observed in TC003 data (already correctly formatted)
}


def tier1_auto_fix(issue: dict) -> dict | None:
    """
    Attempts a deterministic, high-confidence auto-fix.
    Returns a fix dict if successful, otherwise None (needs Tier 2).
    """
    qid = issue["question_id"]

    if issue["issue_type"] == "missing_unit_id":
        unit_id = KNOWN_UNIT_IDS.get(qid)
        if unit_id:
            corrected = f"{issue['original_value']}::{unit_id}"
            return {
                "question_id": qid,
                "action": "auto_fix",
                "original_value": issue["original_value"],
                "corrected_value": corrected,
                "confidence": "high",
                "tier": 1
            }

    if issue["issue_type"] == "whitespace_only_value":
        return {
            "question_id": qid,
            "action": "auto_fix",
            "original_value": issue["original_value"],
            "corrected_value": "",
            "confidence": "high",
            "tier": 1,
            "note": "Whitespace normalized to empty - still needs Care Manager input"
        }

    return None


def tier2_ai_suggestion(issue: dict, structured: dict) -> dict:
    """
    Uses Azure OpenAI to suggest a value for issues that Tier 1
    cannot deterministically resolve - using full submission
    context for clinically-aware suggestions.
    """

    prompt = f"""
    You are helping correct a healthcare assessment submission error.

    Issue: Question ID {issue['question_id']} has problem type
    "{issue['issue_type']}" - {issue['description']}

    Full submission context (other answered questions):
    {json.dumps(structured['answered_questions'])}

    Member ID: {structured['member_id']}
    Template ID: {structured['template_id']}

    This field is a mandatory field that was left empty. Based on
    the type of issue and any context available, provide a brief,
    actionable suggestion for the Care Manager - do NOT invent a
    specific clinical value with confidence; instead explain what
    needs to be filled in and why, in one or two sentences.

    Respond ONLY in this exact JSON format, no other text:
    {{
      "suggestion": "your one-to-two sentence suggestion for the care manager",
      "auto_fillable": false
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
                "content": "You are a careful clinical data quality "
                            "assistant. You never invent clinical values. "
                            "Respond only with valid JSON, no markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 200
    }

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    result = response.json()

    raw_text = result["choices"][0]["message"]["content"].strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        ai_result = json.loads(raw_text)
    except json.JSONDecodeError:
        ai_result = {
            "suggestion": f"Could not parse AI response: {raw_text}",
            "auto_fillable": False
        }

    return {
        "question_id": issue["question_id"],
        "action": "suggest",
        "original_value": issue["original_value"],
        "suggestion": ai_result.get("suggestion"),
        "confidence": "medium",
        "tier": 2
    }


def correction_agent(structured: dict, format_issues: list, classification: str) -> list:
    """
    Runs the two-tier correction strategy on all format issues,
    but only for submissions classified as USER_ERROR.
    """
    if classification != "USER_ERROR":
        return []

    corrections = []

    for issue in format_issues:
        fix = tier1_auto_fix(issue)
        if fix:
            corrections.append(fix)
        else:
            suggestion = tier2_ai_suggestion(issue, structured)
            corrections.append(suggestion)

    return corrections


def main():
    test_cases = load_test_cases()

    print("=" * 65)
    print("   AGENT 4: AI CORRECTION AGENT — Test Run")
    print("=" * 65)

    for case in test_cases:
        structured = intake_agent(case["submission"])
        format_issues = format_validator_agent(structured)
        classification = case["expected_classification"]  # using known label for this test

        corrections = correction_agent(structured, format_issues, classification)

        print(f"\n📋 {case['test_id']}: {case['description']}")
        print("-" * 65)
        print(f"  Classification: {classification}")

        if classification != "USER_ERROR":
            print("  ⏭️  Skipped - not a USER_ERROR (handled by Notification/Ticket agents)")
            continue

        if not corrections:
            print("  ✅ No corrections needed")
            continue

        for c in corrections:
            if c["action"] == "auto_fix":
                print(f"  🔧 Q{c['question_id']}: AUTO-FIXED "
                      f"'{c['original_value']}' -> '{c['corrected_value']}' "
                      f"(Tier {c['tier']}, confidence: {c['confidence']})")
            else:
                print(f"  💡 Q{c['question_id']}: SUGGESTED "
                      f"\"{c['suggestion']}\" "
                      f"(Tier {c['tier']}, confidence: {c['confidence']})")

    print("\n" + "=" * 65)


if __name__ == "__main__":
    main()