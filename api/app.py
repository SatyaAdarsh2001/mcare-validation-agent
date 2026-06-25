"""
mCare Validation Agent - REST API

Exposes the multi-agent validation pipeline as a single HTTP
endpoint, ready for integration with mCare's .NET backend via
a simple HTTP POST call.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from flask import Flask, request, jsonify
from flask_cors import CORS
from orchestrator import run_validation_pipeline

app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "mCare Validation Agent",
        "status": "running",
        "endpoints": {
            "/validate": "POST - validate a single assessment submission"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


@app.route("/validate", methods=["POST"])
def validate():
    """
    Expects JSON body:
    {
      "submission": { ... raw mCare submission JSON ... },
      "known_error": "optional CCA error message string"
    }
    """
    data = request.get_json()

    if not data or "submission" not in data:
        return jsonify({
            "error": "Request body must include a 'submission' object"
        }), 400

    submission = data["submission"]
    known_error = data.get("known_error", "")

    try:
        report = run_validation_pipeline(submission, known_error)
        return jsonify(report), 200
    except Exception as e:
        return jsonify({
            "error": "Validation pipeline failed",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)