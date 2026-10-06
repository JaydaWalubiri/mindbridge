# MindBridge

WhatsApp-based mental health support for adolescent boys in informal settlements, with a web workspace for counsellors and administrators.

Participants use WhatsApp for mood check-ins and counselling requests. Counsellors review mood history, alerts and appointments. Administrators manage counsellor eligibility and system operations.

## Technology

Python and Django; Django templates, HTML and CSS; PostgreSQL for deployment and SQLite for local development; Turn.io for WhatsApp integration.

## Project status

The core application is implemented on `feat/full-stack-care-workspace` and is under review in [PR #1](https://github.com/JaydaWalubiri/mindbridge/pull/1). Model adapters, real Turn acceptance testing and deployment remain pending. The browser chat simulator is for local staff review.

## Quick start

From the repository folder in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_DEBUG = "1"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open http://127.0.0.1:8000/login/. For an existing installation or Linux/macOS, follow the [setup guide](docs/SETUP.md).

## Documentation

- [Local setup](docs/SETUP.md) and [application walkthrough](docs/REVIEW_GUIDE.md)
- [Project map](docs/PROJECT_MAP.md) and [architecture](docs/ARCHITECTURE.md)
- [Turn.io integration](docs/TURN_INTEGRATION.md) and [model integration](docs/MODEL_INTEGRATION.md)
- [Proposal comparison](docs/PROPOSAL_REVIEW.md) and [roadmap](docs/ROADMAP.md)
- [Contribution workflow](CONTRIBUTING.md)

Track tasks in [Issues](https://github.com/JaydaWalubiri/mindbridge/issues) and delivery groups in [Milestones](https://github.com/JaydaWalubiri/mindbridge/milestones).
