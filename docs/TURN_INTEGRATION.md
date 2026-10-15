# Turn.io integration


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


Provider references: [Turn webhooks](https://whatsapp.turn.io/docs/api/webhooks), [Turn messages](https://whatsapp.turn.io/docs/api/messages).
