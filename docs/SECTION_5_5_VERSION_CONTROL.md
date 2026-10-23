# CHAPTER FIVE: IMPLEMENTATION AND EVALUATION
## 5.5 VERSION CONTROL & IMPLEMENTATION EVIDENCE

---

### 5.5.1 Repository Setup and Access

Version control is an indispensable software engineering discipline that ensures collaborative traceability, continuous auditing, and reproducible implementation. For the MindBridge mental health platform—which combines Django-based clinical care workflows with fine-tuned NLP models for adolescent boys in Nairobi informal settlements—the project was managed using Git for local source tracking and hosted on GitHub. GitHub was selected because it natively unifies issue tracking, milestone management, code review workflows through pull requests, and automated continuous integration (CI) test execution. 

The primary repository is hosted at [Project Repository](https://github.com/JaydaWalubiri/mindbridge) under the repository identifier `JaydaWalubiri/mindbridge`. Formal assessor and supervisor access was configured via repository permissions, allowing external reviewers to inspect the commit trajectory, branch history, and automated testing results.

```
[INSERT SCREENSHOT HERE: Half-page width]
Figure 5.1: Repository overview for the MindBridge care platform showing the primary branch, recent commits, and root directory structure.
```

Figure 5.1 illustrates the repository landing page on GitHub. The overview confirms that the codebase is systematically structured, that all committed code conforms to clean repository hygiene without leaked credentials, and that the project documentation, dependency manifests, and issue templates are accessible at the repository root.

---

### 5.5.2 Task Planning and Tracking

To translate architectural specifications into discrete, trackable deliverables, task planning was structured into four sequential GitHub Milestones:
1. **Milestone 1: Core workflows and UI** (Adolescent onboarding, minor assent, round-robin counsellor assignment, and clinical review dashboards).
2. **Milestone 2: Model integration** (Fine-tuned Uliza conversation model, DistilBERT sentiment classification, and Tier-1 crisis routing).
3. **Milestone 3: Evaluation and deployment** (Data handling, PostgreSQL configuration, and end-to-end user acceptance testing).
4. **Milestone 4: Live WhatsApp integration** (Turn.io production webhooks and celery scheduled health check-ins).

Each discrete engineering requirement was registered as an independent GitHub Issue with defined acceptance criteria and verification commands. For example, **Issue #4** (*"Connect the trained conversation model"*) defined the requirements for loading the evaluated Uliza model, managing multi-turn dialogue context across Sheng, Kiswahili, and English, and enforcing safety overrides. Similarly, **Issue #10** (*"Confirm consent and data handling"*) governed the implementation of adolescent assent, location-based health centre routing (Kibera, Mathare, Kawangware), and the 30-day data deletion policy. A GitHub Project Kanban board was utilised to track work items across four states: *Backlog*, *In Progress*, *In Review*, and *Done*.

```
[INSERT SCREENSHOT HERE: Half-page width]
Figure 5.2: GitHub project board and issue tracker showing implementation tasks grouped under Milestones 1 and 2.
```

Figure 5.2 captures the task management board. The evidence demonstrates that features were not implemented ad-hoc; instead, each feature was tied to an open issue with verifiable criteria, moved across status columns as development progressed, and systematically closed upon test verification.

---

### 5.5.3 Branching Strategy

To safeguard the stability of the production codebase, MindBridge adhered to a structured feature-branch workflow. Direct commits to the `main` branch were prohibited. The `main` branch served exclusively as the stable trunk containing tested, deployable code. All new developments, NLP model integrations, and workflow refinements occurred on dedicated, descriptive feature branches branched from `main`.

Branches were named according to their functional scope and associated issue numbers, such as `feat/full-stack-care-workspace`, `feat/turn-whatsapp-integration`, and `fix/sheng-arrival-misunderstandings`. For instance, the core full-stack implementation and language-alignment enhancements were isolated in `feat/full-stack-care-workspace`. This isolation allowed experimental changes—such as tuning the generative temperature, refining regex tokenizers for youth Sheng, and refactoring minor consent prompts—to be tested without destabilising the operational baseline.

```
[INSERT SCREENSHOT HERE: Half-page width]
Figure 5.3: Branch visualization and commit graph depicting feature branch isolation and merge trajectories.
```

As demonstrated in Figure 5.3, the branching strategy clearly isolates parallel workstreams. Features developed on `feat/full-stack-care-workspace` were iteratively verified through automated tests before being merged back into `main` via formal Pull Requests.

---

### 5.5.4 Commits and Development History

MindBridge adopted the **Conventional Commits** specification (`feat`, `fix`, `test`, `chore`, `docs`, `refactor`) to maintain an informative, chronologically coherent development log. Each commit represented a single atomic change, pairing implementation modifications directly with corresponding unit or integration test assertions.

For example, commit `fix(model-server): prioritize loneliness and friendship disclosures over generic school topics` refined the keyword-matching priority in `model_server/app.py`, while commit `fix(language): align participant and bot language with conversational persistence and Sheng prompt tuning` enriched the code-mixing regex and persisted `participant.preferred_language` in the database. Generalised, ambiguous commit messages (such as *"updated code"* or *"fixed stuff"*) were strictly avoided.

```
[INSERT SCREENSHOT HERE: Half-page width]
Figure 5.4: Git commit history illustrating focused, descriptive Conventional Commits and accompanying test validations.
```

Figure 5.4 displays a segment of the repository commit log. The chronological progression demonstrates disciplined iteration: each commit cleanly separates concerns, clearly indicates the component affected (e.g., `model-server`, `language`, `care`, `security`), and provides an immutable audit trail of how conversational resilience and clinical safety features matured.

---

### 5.5.5 Review and Integration

Pull requests (PRs) served as the primary gate for code review, quality assurance, and integration decisions. Every pull request required a completed PR template (standardised under `.github/pull_request_template.md`), linking the relevant issue numbers (e.g., `Closes #4, Closes #10`), documenting the problem addressed, detailing the validation commands executed, and completing a four-point review checklist:
- Acceptance criteria addressed and final diff inspected.
- All automated checks and unit tests passing.
- Database migrations and architectural documentation updated.
- Zero credentials, tokens, or participant records committed.

A dedicated continuous integration pipeline, configured via GitHub Actions in `.github/workflows/test.yml`, automatically triggered upon every push and PR submission. This workflow built the test environment, executed the full 133-test suite covering sentiment classification, Tier-1 crisis routing, counsellor slot booking, and supervised model endpoints, and reported build statuses directly on the PR.

```
[INSERT SCREENSHOT HERE: Half-page width]
Figure 5.5: Pull Request #1 review record showing linked issues, completed validation checklist, and successful GitHub Actions CI status.
```

Figure 5.5 illustrates the integration record for Pull Request #1. The evidence confirms that peer reviews and automated checks were rigorously enforced before changes were approved and integrated into the primary branch.

---

### 5.5.6 Project Organisation and Reproducibility

The repository was organised to uphold the principles of separation of concerns, architectural modularity, and rapid reproducibility across development, testing, and production environments:

```
mindbridge/
├── care/                   # Django clinical workflows, WhatsApp handlers, and risk assessment
├── config/                 # Django core project configuration and ASGI/WSGI endpoints
├── model_server/           # FastAPI authenticated bounded model server for NLP inference
├── models/                 # Fine-tuned Uliza adapter artifacts and sentiment classification models
├── tools/                  # NLP data auditing, dataset balancing, and evaluation scripts
├── templates/              # Clinical review dashboards, counsellor portal, and WhatsApp simulator
├── static/                 # Static CSS stylesheets, JavaScript preview components, and assets
├── docs/                   # Academic specifications, architecture manuals, and deployment guides
├── .github/                # GitHub Actions CI workflows, issue templates, and PR guidelines
├── .env.example            # Sanitized environment template without secrets or credentials
├── .gitignore              # Exclusion rules for virtual environments, secrets, and SQLite files
└── requirements.txt        # Frozen Python dependency manifest
```

Reproducibility is guaranteed through explicit dependency pinning and strict configuration hygiene. The repository tracks [`.env.example`](file:///C:/Users/jadaw/OneDrive/MINDBRIDGE/mindbridge/.env.example), which documents all required environment variables (`DJANGO_SECRET_KEY`, `CONVERSATION_URL`, `RISK_NEGATIVE_THRESHOLD`, `GROQ_API_KEY`) using safe dummy placeholders. The actual active configuration file, [`.env`](file:///C:/Users/jadaw/OneDrive/MINDBRIDGE/mindbridge/.env), is strictly excluded via `.gitignore`, alongside virtual environment binaries (`.venv/`), compiled Python bytecode (`__pycache__/`), and local testing databases (`*.sqlite3`). A new researcher or clinician can reproduce the entire operational system by cloning the repository, creating a virtual environment, running `pip install -r requirements.txt`, running `python manage.py migrate`, and executing `python manage.py test`.

```
[INSERT SCREENSHOT HERE: Half-page width]
Figure 5.6: Project folder architecture and setup documentation demonstrating separation of concerns and reproducible setup.
```

Figure 5.6 depicts the folder structure and documentation in VS Code and GitHub. The evidence demonstrates that the repository is clean, securely configured, and conforms to industry software engineering standards.

---

### 5.5.7 Hosting and Deployment

MindBridge is architected for hybrid deployment across microservices:
1. **Care Service & Clinician Portal**: Powered by Django, hosted using Gunicorn/Uvicorn ASGI behind an Nginx reverse proxy. In local development and prototyping, SQLite is utilised; for hosted staging, PostgreSQL is configured via environment variables (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).
2. **Model Inference Server**: Powered by FastAPI running as a bounded service on port 8001 (`http://127.0.0.1:8001/v1/reply`). The model service operates behind bearer token authentication (`MODEL_SERVICE_TOKEN`), interfacing with local fine-tuned adapters or high-throughput generative APIs (Meta Llama 3 via Groq) while maintaining conversational history and strict token bounds.
3. **WhatsApp Messaging Gateway**: Interfaces with Turn.io WhatsApp Business API webhooks using HMAC-SHA256 signature verification (`valid_turn_signature`), ensuring that only authenticated WhatsApp messages from adolescent users trigger inbound clinical workflows.

```
[INSERT SCREENSHOT HERE: Half-page width]
Figure 5.7: Active local deployment showing running Django care service, FastAPI model server, and passing interactive test session.
```

Figure 5.7 provides evidence of the operational system. The screenshot displays the concurrent terminal sessions running the Django care server on port 8000 and the FastAPI model server on port 8001, alongside the active WhatsApp preview simulator processing a real-time conversational exchange with zero errors.

---

### 5.5.8 Summary of Version Control Practices

In summary, the version control and implementation practices adopted for MindBridge directly supported the clinical safety, technical robustness, and academic integrity of the platform:
- **Traceability**: Every software change can be traced backward from a commit, through a pull request, to a specific GitHub Issue and planning Milestone.
- **Safety Isolation**: Experimental NLP model fine-tuning and adolescent onboarding iterations were insulated from stable code via feature branching.
- **Quality Assurance**: Automated regression tests guaranteed that critical safety features—such as Tier-1 suicide crisis interception—were never compromised by conversational model improvements.
- **Security & Hygiene**: Zero private participant data, confidential adolescent check-in logs, or API credentials were ever committed to repository history.
