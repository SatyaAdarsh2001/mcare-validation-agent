# 🏥 mCare Validation Agent

<div align="center">

![Python](https://img.shields.io/badge/Python-3.14-blue?style=for-the-badge&logo=python&logoColor=white)
![Azure](https://img.shields.io/badge/Azure_OpenAI-0078D4?style=for-the-badge&logo=microsoftazure&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-REST_API-000000?style=for-the-badge&logo=flask&logoColor=white)
![Status](https://img.shields.io/badge/Status-Active_Development-success?style=for-the-badge)

> **A multi-agent AI system that validates, classifies, and corrects healthcare assessment submission errors before they reach the CCA system — built and tested against real production error patterns.**

</div>

---

## 📌 The Problem

Care Managers using the **mCare** application submit clinical assessments (e.g., the Columbia Suicide Severity Risk Screener) to the upstream **CCA (CareAdvance)** system via REST API. A significant share of these submissions fail — for reasons ranging from simple data-entry mistakes to backend infrastructure issues — with no automated way to catch, classify, or resolve them before failure.

This project analyzes **real production error logs** and builds an agentic AI pipeline that intercepts a submission, figures out exactly *why* it would fail, and either fixes it, suggests a fix, or routes it to the right team.

---

## ✨ What It Does

| Capability | Description |
|---|---|
| 🔍 **Structural Parsing** | Reads raw submission JSON and extracts member/template metadata |
| ✅ **Format Validation** | Catches missing units, blank mandatory fields, whitespace-only values |
| 🧠 **AI Classification** | Uses Azure OpenAI to classify each error as `USER_ERROR`, `TEMPLATE_ISSUE`, or `SYSTEM_ISSUE` |
| 🔧 **Two-Tier Correction** | Auto-fixes deterministic format issues; AI-suggests fixes for context-sensitive ones (never auto-fills clinical data) |
| 📋 **Audit Reporting** | Produces a structured report — issues found, what was fixed, what needs human review |
| 🌐 **REST API** | Exposes the full pipeline as a single HTTP endpoint, ready for `.NET` integration |

---

## 🧪 Validated Against Real Production Errors

This isn't built on synthetic data. The 7 test cases in [`data/test_submissions.json`](data/test_submissions.json) are derived directly from real mCare → CCA submission failure logs.

| Test Case | Real Error Pattern | AI Classification | Result |
|---|---|---|---|
| TC001 | Missing unit ID (`20` instead of `20::505`) | `USER_ERROR` | ✅ Auto-fixed |
| TC002 | Multiple empty mandatory fields | `USER_ERROR` | ✅ AI suggestion |
| TC003 | `DBTimeoutException` | `SYSTEM_ISSUE` | ✅ Escalated to Infra team |
| TC004 | `Invalid Session` | `SYSTEM_ISSUE` | ✅ Escalated to Infra team |
| TC005 | Answer count (122) ≠ template count (120) | `TEMPLATE_ISSUE` | ✅ Escalated to Template team |
| TC006 | `Invalid Question Id: 263` | `TEMPLATE_ISSUE` | ✅ Escalated to Template team |
| TC007 | Whitespace submitted instead of a numeric value | `USER_ERROR` | ✅ AI suggestion |

**Result: 7/7 (100%) correctly classified** by the Classifier Agent.

---

## 🏗️ Architecture

```
        mCare Submission JSON
                 |
                 v
        +----------------------+
        | Agent 1: Intake      |  Parses structure, finds blank fields
        +----------+-----------+
                   v
        +----------------------+
        | Agent 2: Format     |  Mandatory fields, unit formats, whitespace
        | Validator            |
        +----------+-----------+
                   v
        +----------------------+
        | Agent 3: Classifier  |  Azure OpenAI decides the category
        +----------+-----------+
                   v
      +------------+------------+
      v            v            v
 USER_ERROR    TEMPLATE     SYSTEM_ISSUE
      |          ISSUE           |
      v            |             |
+-----------+      v             v
| Agent 4:  |   +---------------------+
| Correction|   | Agent 6/7:          |
+-----+-----+   | Notify + Ticket     |
      v          | (stretch goals)     |
+-----------+   +---------------------+
| Agent 5:  |
| Report    |
+-----------+
```

Each agent has a single responsibility and is built from first principles in Python — no LangChain/CrewAI — with Azure OpenAI (`gpt-4.1-mini`) used purely as the reasoning layer for classification and context-aware suggestions.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| AI Model | Azure OpenAI — GPT-4.1-mini (HIPAA-eligible) |
| API | Flask + Flask-CORS |
| HTTP Client | `requests` (direct REST calls to Azure OpenAI) |
| Config | `python-dotenv` |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- An Azure OpenAI resource with a deployed chat model

### Installation

```bash
git clone https://github.com/SatyaAdarsh2001/mcare-validation-agent.git
cd mcare-validation-agent

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

### Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your own credentials:

```env
AZURE_OPENAI_KEY=your_azure_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
```

### Run the Agent Pipeline Directly

```bash
python src/agents/report_agent.py
```

This runs all 7 test cases through the full 5-agent pipeline and saves results to `data/validation_reports.json`.

### Run as a REST API

```bash
python api/app.py
```

Then send a request:

```bash
curl -X POST http://127.0.0.1:5000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "submission": {
      "member_id": "FLO202759913501",
      "id": 922,
      "version": 33,
      "QUESTIONS": [{"id": 395, "value": "20"}]
    },
    "known_error": "Unit ID must be present for a concept of type 4"
  }'
```

---

## 📁 Project Structure

```
mcare-validation-agent/
|
├── api/
│   └── app.py                       # Flask REST API
|
├── src/
│   ├── orchestrator.py              # Runs the full agent pipeline
│   └── agents/
│       ├── intake_agent.py          # Agent 1 - parses submission
│       ├── format_validator_agent.py# Agent 2 - rule-based checks
│       ├── classifier_agent.py      # Agent 3 - AI classification
│       ├── correction_agent.py      # Agent 4 - two-tier correction
│       └── report_agent.py          # Agent 5 - final report
|
├── data/
│   ├── test_submissions.json        # 7 real production error test cases
│   └── validation_reports.json      # Generated output reports
|
├── .env.example                     # Safe environment variable template
├── requirements.txt
└── README.md
```

---

## 🗺️ Roadmap

- [x] Agent 1 — Intake
- [x] Agent 2 — Format Validator
- [x] Agent 3 — Classifier (USER_ERROR / TEMPLATE_ISSUE / SYSTEM_ISSUE)
- [x] Agent 4 — Two-tier AI Correction
- [x] Agent 5 — Report Agent
- [x] Flask REST API
- [ ] Agent 6 — Notification Agent (email routing by issue type)
- [ ] Agent 7 — Ticket Agent (automated iServe ticket creation)
- [ ] Simple frontend for live demo
- [ ] SQLite persistence layer for audit history

---

## 🔐 Security Notes

- Azure OpenAI (not the public ChatGPT product) is used — Microsoft does not use API request data to train models, and the service is HIPAA-eligible.
- The Correction Agent is intentionally designed to **never auto-fill clinical/sensitive values** — it only auto-fixes deterministic format issues and surfaces suggestions for human confirmation otherwise.

---

## 👨‍💻 Author

**Satya Adarsh Bikkina**
Healthcare Data Integration → GenAI Developer

[![GitHub](https://img.shields.io/badge/GitHub-SatyaAdarsh2001-181717?style=for-the-badge&logo=github)](https://github.com/SatyaAdarsh2001)

