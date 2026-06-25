"""
Orchestrator
Runs the full 5-agent pipeline on a single submission and
returns the final validation report. This is what the Flask
API calls for each incoming request.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

from agents.intake_agent import intake_agent
from agents.format_validator_agent import format_validator_agent
from agents.classifier_agent import classifier_agent
from agents.correction_agent import correction_agent
from agents.report_agent import report_agent


def run_validation_pipeline(submission: dict, known_error: str = "") -> dict:
    """
    Runs the full pipeline on a single raw submission dict.

    submission:  the raw mCare/CCA submission JSON
    known_error: optional - the raw CCA error message, if this is
                 being run after a real rejection (used by the
                 Classifier Agent for extra context)
    """

    # Agent 1: Intake
    structured = intake_agent(submission)

    # Agent 2: Format Validator
    format_issues = format_validator_agent(structured)

    # Agent 3: Classifier
    classification_result = classifier_agent(structured, format_issues, known_error)
    classification = classification_result.get("classification", "UNKNOWN")

    # Agent 4: Correction
    corrections = correction_agent(structured, format_issues, classification)

    # Agent 5: Report
    # report_agent expects a "case" dict with test_id/known_error - we
    # build a minimal one here since this is a live submission, not a
    # pre-labeled test case
    pseudo_case = {
        "test_id": submission.get("member_id", "UNKNOWN") + "-" + str(submission.get("id", "")),
        "known_error": known_error
    }

    report = report_agent(pseudo_case, structured, format_issues, classification, corrections)

    # Attach the classifier's own reasoning/confidence to the report
    report["classifier_confidence"] = classification_result.get("confidence")
    report["classifier_reasoning"] = classification_result.get("reasoning")

    return report