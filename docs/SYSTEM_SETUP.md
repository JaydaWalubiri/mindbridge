# Run the whole MindBridge system

Start with a **local fictional demo**, as requested. The participant simulator, counsellor/admin screens, keyword and mood rules, optional English DistilBERT sentiment, guarded conversation client, Turn webhook/queue, and scheduled-worker implementation are connected in code. Actual WhatsApp delivery and GPU hosting still require your accounts and endpoints.

## 1. Pull the application on Windows

Stop Django. In PowerShell in your repository:

```powershell
git status -sb
git fetch origin
git switch feat/full-stack-care-workspace
git pull --ff-only origin feat/full-stack-care-workspace
```

If Git reports local changes, commit or stash those changes before switching; do not discard them. After the integration pull request is merged, this application branch contains the complete changes. Before merge, use `feat/safe-conversation-model` instead.

If `.venv\Scripts\python.exe` is missing, run `py -3.12 -m venv .venv`. Then:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_DEBUG = '1'
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py add_keywords
.\.venv\Scripts\python.exe manage.py check_system
.\.venv\Scripts\python.exe manage.py runserver
```

Create a superuser only if you do not already have one. `seed_demo` creates fictional records and an eligible profile for the first superuser. It does not create passwords. Production/Turn/model/worker warnings from `check_system` are expected during a local demo.

## 2. Review the complete local journey

Sign in at `http://127.0.0.1:8000/login/`.

1. Open **Availability** and add a future 30-minute slot for the counsellor who will receive demo assignments.
2. Open the staff-only **WhatsApp flow preview** at `/preview/whatsapp/`. This saves clearly marked demo records and never queues messages to Turn, even if Turn credentials exist.
3. Agree, choose a fictional nickname and adult age, enter a mood score, and send a fictional English note. Onboarding assigns an eligible active counsellor automatically. Inspect the participant profile and mood history.
4. Choose **Counsellor**. The request appears on the assigned counsellor dashboard; numbered future slots appear in chat. Select a slot and verify it on **Sessions**. If there are no slots, the request waits for staff.
5. With a new fictional demo conversation, use `I feel hopeless about school` to inspect Tier-2 behaviour. This phrase alone should not create a combined alert without another eligible layer. Use the direct safety phrase `I intend to take my own life today` to verify immediate emergency guidance and an alert, then verify **Counsellor** and slot selection still work.
6. Review the alert outcome, pause check-ins, and inspect privacy/deletion options. Urgent guidance does not claim an appointment or staff action has already happened.

Participants use normal WhatsApp in a live setup. The web WhatsApp-style interface remains a restricted staff testing tool.

## 3. Enable the English sentiment baseline

In the same PowerShell window, stop Django first:

```powershell
.\.venv\Scripts\python.exe -m pip install 'torch>=2.6,<3' --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-sentiment.txt
$env:SENTIMENT_ENABLED = '1'
$env:SENTIMENT_RISK_ENABLED = '0'
.\.venv\Scripts\python.exe manage.py check_sentiment --download
.\.venv\Scripts\python.exe manage.py runserver
```

The baseline needs no GPU. Scores and their source appear on the participant profile. It is mainly English and is not a clinical classifier. Non-English/short-text predictions are excluded from risk. Project fine-tuning still needs independent reviewed labels: the prepared DistilBERT notebook and blank labelling template are not a trained project model.

For **fictional integration testing only**, `SENTIMENT_RISK_ENABLED=1` allows eligible English negative scores at 0.85 or above to supply one layer. Tier-2 keyword evidence supplies another. Restore `0` until evaluation and review are complete. Mood exceptions and Tier-1 urgency do not depend on this setting. Turning the setting off also excludes older experimental sentiment evidence from new decisions.

## 4. Connect the trained conversation adapter

Follow [CONVERSATION_SETUP.md](CONVERSATION_SETUP.md). The adapter is saved and revision-pinned; do not restart Kaggle training. You need a private, authenticated GPU service URL. Hugging Face's model page is not a running API. Run `check_conversation` after setting its URL and service token.

The candidate is for supervised testing. Native-language and clinician review, broader held-out tests, and real-host latency checks remain. The known Sheng late-arrival mistake now uses a labelled contextual script. Raw generations can still misunderstand new situations; the October 13 experimental repair was not selected. See `docs/CONVERSATION_SETUP.md` for the distinction between scripted regressions and model evaluation.

## 5. Run jobs and prepare PostgreSQL hosting

For a local fictional demo, run once while Django is stopped:

```powershell
.\.venv\Scripts\python.exe manage.py run_workers --once
.\.venv\Scripts\python.exe manage.py check_system
```

This executes delivery, check-ins, escalation and retention. Do not run it against actual contacts unless delivery is authorized: it sends queued messages when Turn credentials are present. Demo simulator records never send messages. Retention removes expired data according to the documented policy.

For a Linux host with Docker Compose, the repository includes `Dockerfile`, `compose.yaml` and `requirements-production.txt`. Copy `.env.example` to `.env`, set unique database/password/secret values, set `DJANGO_DEBUG=0`, and configure your allowed hostname, HTTPS and trusted origins. Compose reads `.env`; plain Django still reads process environment variables.

```bash
docker compose build
docker compose up -d
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py add_keywords
docker compose exec web python manage.py check_sentiment --download
docker compose exec web python manage.py check_system --connections --strict
docker compose logs --tail 100 worker
```

The stack starts PostgreSQL, applies migrations, runs Gunicorn/collected static files, and starts one worker. The worker runs delivery every minute, check-ins/retention daily, and escalation every 15 minutes. Job success/failure is visible in the admin workspace and readiness command. Failed jobs retry after a minute without logging participant/provider error text.

The web port binds to localhost. A trusted HTTPS reverse proxy, public hostname, monitoring and backups still need setup. Set `DJANGO_TRUST_PROXY=1` only when that proxy overwrites forwarding headers; set `DJANGO_HTTPS_ONLY=1` and `DJANGO_CSRF_TRUSTED_ORIGINS=https://YOUR-HOST`. Never expose PostgreSQL or the model service publicly without access control. Do not start a second worker. Continuous workers require PostgreSQL.

## 6. Connect real WhatsApp last

Follow [TURN_INTEGRATION.md](TURN_INTEGRATION.md). You must supply through private environment/secret settings:

- Your authorized Turn.io WhatsApp account/number and scoped API token.
- The webhook signing secret and public HTTPS Django URL ending `/webhooks/turn/`.
- Approved check-in, appointment, staff-notice and overdue-support templates, their namespace and language.
- Eligible counsellor accounts, availability and explicit staff notification opt-in.
- Authorized test contacts and a staffed safeguarding/consent plan.

Use `check_system --connections` to check configuration and fictional model calls. It never sends a WhatsApp test message, and configured templates are not proof of provider approval. With authorized contacts, verify onboarding, a reply, mood note, request, booking, staff alert, retries, pause and delivery on actual WhatsApp before calling the live system ready.

## What has been verified

Local SQLite application tests, signed-webhook integration, mocked classifier/generator/provider boundaries, duplicate handling, hybrid evidence, urgent booking, model source display, worker status and migration consistency. CI also tests PostgreSQL and validates Compose configuration. Software tests do not establish clinical effectiveness, multilingual accuracy, provider approval or live-host availability.
