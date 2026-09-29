# MindBridge

A Django application for a WhatsApp check-in flow, counsellor workspace, and administrator dashboard. The non-model workflow includes a signed Turn.io webhook, an outbound queue with retries, weekly check-ins, session requests and review alerts. The trained classifier and conversational model are separate adapters.

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Windows PowerShell: $env:DJANGO_DEBUG="1"
# macOS/Linux: export DJANGO_DEBUG=1
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/login/`. The counsellor workspace is `/`, administrator operations are `/workspace-admin/`, and the WhatsApp visual preview is `/preview/whatsapp/`. The preview is scripted and does not send real messages. `/admin/` provides staff accounts, participant assignments, keyword settings, queue inspection and weekly check-in records. Only accounts with `is_staff` can open the admin dashboard; counsellors see their assigned participants.

For fictional example records, run `python manage.py seed_demo`. They are local sample data. Tests run with `python manage.py test`.

## Turn.io setup

1. Deploy Django at a public HTTPS address with PostgreSQL and run migrations. Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG=0`, `DJANGO_HTTPS_ONLY=1` and PostgreSQL credentials. Do not use the local development server for the webhook.
2. In Turn.io **Settings → API & Webhooks**, create a `whatsapp` inbound webhook to `https://YOUR-DOMAIN/webhooks/turn/`. Set its HMAC secret as `TURN_WEBHOOK_SECRET` on the server. Create an API token and set `TURN_API_TOKEN`. Keep both out of Git.
3. Run `python manage.py deliver_outbound` once a minute as an independent scheduled worker. The webhook returns after saving messages; the worker sends accepted replies, retries temporary errors up to five times and exposes failures in `/workspace-admin/` and `/admin/care/outboundmessage/`. Do not run multiple SQLite workers in production; use PostgreSQL. A message marked *sent* means Turn accepted it, not that a participant read it.
4. Approve a WhatsApp template for a weekly check-in prompt. It should have **no placeholders** and invite the person to reply with a mood score. Configure `TURN_TEMPLATE_NAMESPACE`, `TURN_CHECKIN_TEMPLATE_NAME` and `TURN_TEMPLATE_LANGUAGE` from the actual approved template. Run `python manage.py run_checkins` once a day (Africa/Nairobi timezone), followed by the outbound worker. The command is safe to rerun. It queues one Monday prompt per opted-in participant, records completed or missed weeks and flags two consecutive missed weeks for counsellor review. Without an approved template, it still tracks weeks but does not send a scheduled message.
5. For session confirmation outside a recent WhatsApp conversation, approve a second template whose **one body placeholder** is the appointment time. Set `TURN_SESSION_TEMPLATE_NAME`. A session booked within 23 hours of an inbound message can use a regular text reply. Otherwise, the dashboard tells staff to confirm manually if no template is configured.
6. Send a real message to your Turn number. Check that the webhook creates a participant, that consent buttons appear and work, and that the outbound queue marks the reply accepted. Assign the new participant to a counsellor in `/admin/` and verify their dashboard. Conduct this test only with authorized test contacts and an agreed escalation process.

The flow accepts `I agree`, `Not now`, scores `1`–`5`, `Counsellor`, `Check in`, and `Pause`. Buttons are sent where supported. Inbound message IDs prevent duplicate check-ins on webhook retries. The webhook does not call the Turn API itself. Turn's five-second webhook deadline and outbound template format are documented in its [webhook](https://whatsapp.turn.io/docs/api/webhooks) and [message](https://whatsapp.turn.io/docs/api/messages) references.

## Model handoff

`care/model_ports.py` provides `classify_note(text)` and `generate_response(text, context)`. They currently return `None`, so the application stores mood and notes, applies configured keyword and mood rules, and uses a scripted fallback reply. When trained models are evaluated, implement those two adapters and test their output and safety handling before live use. No model confidence or diagnosis is fabricated. The counsellor remains responsible for reviewing alerts and arranging care. The optional classifier label is stored in `MoodEntry` when an adapter is connected.

## Production notes

Store credentials only in the deployment environment. Protect sender identifiers and notes with access controls, encryption, backups, retention rules and a privacy review. Provide a monitored staff alert process before a live pilot; the dashboard is a review queue, not an emergency response service. The queued send is at least once on an ambiguous network failure: a process crash after Turn accepts a message but before the database commit can lead to a duplicate. See [architecture](docs/ARCHITECTURE.md) and [roadmap](docs/ROADMAP.md).
