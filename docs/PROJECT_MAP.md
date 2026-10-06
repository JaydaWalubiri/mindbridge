# Project map

One Django application contains the care workflows. Keep the familiar Django filenames and avoid another frontend project, duplicated versions, or deeply nested service layers.

## Backend, frontend and documentation

| Part | Location | What is inside |
| --- | --- | --- |
| Backend | `care/` | Database models, views, services, risk rules and tests |
| Backend configuration | `config/` | Django settings and main URL routes |
| Frontend screens | `templates/care/` | Counsellor, admin and demo chat pages |
| Frontend login | `templates/registration/` | Login page |
| Frontend styling | `static/care/` | Shared CSS |
| Documentation | `docs/` | Setup, walkthrough, architecture and project notes |
| GitHub setup | `.github/` | Automated checks and issue/PR templates |
| Run the application | `manage.py` | Django commands |
| Python packages | `requirements.txt` | Required dependencies |
| Environment settings | `.env.example` | Setting names and placeholders |
| Contribution guide | `CONTRIBUTING.md` | Branches, commits and pull requests |

The backend and frontend belong to the same Django project. These folders keep Django's standard layout. You do not need another frontend server. Start with `care/` for Python logic, `templates/` for pages and `static/` for styles.

## Find a feature

| Component | Backend | UI |
| --- | --- | --- |
| Data records | `care/models.py`, `care/migrations/` | Django admin registrations in `care/admin.py` |
| Login and permissions | `config/urls.py`, `care/views.py` | `templates/registration/login.html` |
| WhatsApp webhook | `care/views.py`, `care/urls.py` | Participants use WhatsApp |
| Consent, nickname, age, messages | `care/services.py` | `templates/care/whatsapp_preview.html` for local tests |
| Round-robin assignment | `care/workflows.py` → `assign_counsellor` | Admin dashboard, counsellor profiles |
| Available times and booking | `care/workflows.py` → appointment functions; `care/forms.py` | `availability.html`, `book_session.html`, `sessions.html` |
| Risk decisions | `care/risk.py` | `alerts.html`, `participant.html` |
| Alert review and requests | `care/views.py` | `dashboard.html`, `alerts.html` |
| Queue and Turn delivery | `care/services.py` | Admin dashboard and outbound records |
| Staff notices and escalation | `care/workflows.py` | Admin overdue-alert list |
| Privacy and data deletion | `care/workflows.py` → `enforce_retention` | Admin deletion-request list |
| Model integration | `care/model_ports.py` | Scripted fallback until integration |
| Scheduled jobs | `care/management/commands/` | Operational status in admin |
| Tests | `care/tests.py` | No production UI |

## File rules

- Use lowercase Python filenames with underscores and descriptive HTML names.
- Keep one source of truth for a workflow; the simulator calls the same message handler as Turn.
- Commit Django migrations with the feature. Never rename or rewrite a migration already published/applied elsewhere.
- Keep styles in `static/care/app.css`; templates stay under `templates/care`.
- Keep training datasets and model weights in their approved storage/Hub repositories. Document their identifiers when integrated; do not copy checkpoints into the web app repo.
- Add new modules only when a responsibility no longer fits clearly in the current small files.
