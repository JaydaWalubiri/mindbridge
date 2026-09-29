# MindBridge

A Django application for a WhatsApp based check-in flow, counsellor workspace, and administrator dashboard. This repository is a reviewable development build. It uses a scripted user flow and basic review rules while the classifier is being trained.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# macOS/Linux: export DJANGO_DEBUG=1
# Windows PowerShell: $env:DJANGO_DEBUG="1"
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/login/`. Sign in with the account you created. The counsellor workspace is at `/`, the administrator dashboard is at `/workspace-admin/`, and the interactive WhatsApp **preview** is at `/preview/whatsapp/`. The preview does not send messages or write records. Use `/admin/` to add counsellor accounts, assign participants, review check-ins and alerts, and maintain keywords. Reserve the `is_staff` flag for administrators; ordinary active counsellors see only participants assigned to them.

To populate a few **fictional** dashboard records locally, run `python manage.py seed_demo`. This creates sample participants assigned to the first superuser; it is idempotent and does not create a password.

For PostgreSQL, set `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and optionally `POSTGRES_PORT`. Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG=0`, and `DJANGO_HTTPS_ONLY=1` before deployment. SQLite is only the default for local development. Production additionally needs HTTPS, a static file server, database backups, access logging, encryption and retention controls for identifiers and notes, and a privacy review before any real personal data is used.

## WhatsApp / Turn.io integration

1. In Turn.io, create a `whatsapp` inbound webhook pointing to your HTTPS URL ending `/webhooks/turn/`.
2. Configure `TURN_WEBHOOK_SECRET` with the webhook HMAC secret and `TURN_API_TOKEN` with a scoped API token in your deployment environment. Never commit these values.
3. The first message prompts for explicit consent. Reply `I agree` to opt in, then send a mood score from `1` to `5`. An additional note is optional; a participant can write `Talk to a counsellor` or `Check in again` at any time, and `Pause check-ins` withdraws consent. The preview displays suggested reply buttons; the signed webhook currently sends text prompts and accepts those same phrases. The webhook stores the message ID for retry safety and sends a reply via Turn's `/v1/messages` API if a token is configured.
4. Assign newly registered participants to a counsellor in the admin interface. No automatic assignment or outbound scheduled prompts are implemented yet.

The flow is described in [ARCHITECTURE.md](docs/ARCHITECTURE.md). Local tests work without a Turn account: `python manage.py test`.

## Data handoff

The webhook stores check-ins in `MoodEntry` and creates `RiskAlert` records for configured keyword and mood signals. The classifier can later fill `sentiment_label` and `sentiment_score`; no untrained model scores are generated now. The documented two-of-three decision logic and missed check-in scheduling are **future work**. Scheduling currently creates a `Session` row but does not send a WhatsApp confirmation. This application must not be presented as a clinical triage service.

For an existing backend, map these fields to its Django models; do not create duplicate production participant records. Review [ROADMAP.md](docs/ROADMAP.md) for milestones and the remaining work before a live pilot.
