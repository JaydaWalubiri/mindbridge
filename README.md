# MindBridge

WhatsApp mental health support with a Django counsellor workspace and administrator dashboard. Participants use **normal WhatsApp**, not a participant website. The local WhatsApp simulator exists for staff to review fictional journeys.

## Start here

- [Run and review the application](docs/REVIEW_GUIDE.md)
- [Where each component lives](docs/PROJECT_MAP.md)
- [Proposal requirements and implementation status](docs/PROPOSAL_REVIEW.md)
- [Git branches, commits and pull requests](CONTRIBUTING.md)
- [System architecture](docs/ARCHITECTURE.md)
- [Remaining milestones](docs/ROADMAP.md)

## Run locally — Windows PowerShell

From the `mindbridge` folder:

```powershell
# First setup only:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Each new PowerShell session:
$env:DJANGO_DEBUG = "1"
.\.venv\Scripts\python.exe manage.py migrate
# First setup only: create an administrator account.
.\.venv\Scripts\python.exe manage.py createsuperuser
# Optional: clearly fictional records and a demo counsellor profile.
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

For an existing checkout, stop Django, run `git status -sb` and then `git pull --ff-only` if your working tree is clean; reinstall requirements and run migrations before restarting. See the review guide for account and participant steps. No account passwords are shipped.

macOS/Linux: use `python -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`, `export DJANGO_DEBUG=1`, then the same `python manage.py ...` commands.

| Screen | Local URL |
| --- | --- |
| Login | http://127.0.0.1:8000/login/ |
| Counsellor overview and requests | http://127.0.0.1:8000/ |
| Alerts and review feedback | http://127.0.0.1:8000/alerts/ |
| Participants and profiles | http://127.0.0.1:8000/participants/ |
| Appointments | http://127.0.0.1:8000/sessions/ |
| Counsellor availability | http://127.0.0.1:8000/availability/ |
| Administrator operations | http://127.0.0.1:8000/workspace-admin/ |
| Django record management | http://127.0.0.1:8000/admin/ |
| Staff-only local participant simulator | http://127.0.0.1:8000/preview/whatsapp/ |

## Turn.io connection

1. Deploy Django behind public HTTPS with PostgreSQL and run migrations. Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG=0`, `DJANGO_HTTPS_ONLY=1` and database environment variables. `.env.example` documents names only; the app reads process environment variables, not a `.env` file automatically.
2. Configure a `whatsapp` inbound webhook at `https://YOUR-DOMAIN/webhooks/turn/`. Store its HMAC secret as `TURN_WEBHOOK_SECRET`, and the API token as `TURN_API_TOKEN`. Never commit actual credentials.
3. Create a **Counsellor profile** in Django admin for each eligible active account. Enable assignment acceptance. Register the staff member's authorized WhatsApp number and notification opt-in only if they should receive staff notices. Add availability through the web workspace; administrators can select a counsellor there.
4. Approve and configure the actual WhatsApp templates:

| Environment setting | Required approved template |
| --- | --- |
| `TURN_CHECKIN_TEMPLATE_NAME` | Weekly prompt; no placeholders; invites a mood score |
| `TURN_SESSION_TEMPLATE_NAME` | Participant appointment confirmation; one body parameter for appointment time |
| `TURN_STAFF_TEMPLATE_NAME` | Staff notice; one body parameter for a brief case-code notification |
| `TURN_SUPPORT_TEMPLATE_NAME` | Support after an overdue alert; no placeholders; includes approved emergency guidance |

Also set `TURN_TEMPLATE_NAMESPACE` and `TURN_TEMPLATE_LANGUAGE` to the provider's actual values. Template approval and account configuration are external prerequisites. Readiness indicators mean settings exist, not that Turn has approved or validated them.

5. Configure independent scheduled commands:

| Command | Frequency | Purpose |
| --- | --- | --- |
| `python manage.py deliver_outbound` | Every minute | Send pending replies/notices with retries |
| `python manage.py run_checkins` | Daily in Africa/Nairobi | Weekly prompts and missed-cycle review |
| `python manage.py run_escalations` | Every 15 minutes | Escalate open alerts after 24 hours |
| `python manage.py enforce_retention` | Daily | Purge old message/mood data and requested profiles |

Do not run concurrent SQLite workers in production. On PostgreSQL the application locks the assignment cursor, participant flow, counsellor booking, and outbound records. An ambiguous gateway success followed by a process crash may still produce a duplicate outbound message.

6. Test with authorized test contacts: onboarding, assignment, mood/note, session request, slot selection, staff review and delivery queue. The local simulator creates `DEMO-CHAT-*` records and **never queues provider messages**, including when templates are configured. It requires staff sign-in and `DJANGO_DEBUG=1`, and is disabled outside development.

## Model handoff

`care/model_ports.py` exposes `classify_note(text)` and `generate_response(text, context)`. Both return `None` until the evaluated models are connected. The application supplies recent conversation context, stores available classification results, and uses explicit rules and scripted replies meanwhile. It never invents model confidence or a diagnosis.

The hybrid decision uses evidence from distinct layers within seven days. Tier-1 keywords override consensus; the proposal's explicit sudden-drop, consecutive-low-weekly-mood and disengagement rules remain standalone review paths. See the proposal comparison for this interpretation and the requirements still awaiting model evaluation.

## Check your changes

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

Do not commit local databases, participant records, secrets, checkpoints or virtual environments. Data collection, safeguarding arrangements and approval for a live pilot remain separate from implementing the prototype.

Provider references: [Turn webhooks](https://whatsapp.turn.io/docs/api/webhooks), [Turn messages](https://whatsapp.turn.io/docs/api/messages).
