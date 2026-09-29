# Architecture

| User | Interface | Workflow |
| --- | --- | --- |
| Participant | WhatsApp via Turn.io | Consent, mood 1–5, optional note, session request, pause |
| Counsellor | Assigned workspace | Mood trends, participant history, alerts and sessions |
| Administrator | Operations dashboard and Django admin | Counsellor accounts, assignments, keywords, delivery queue, check-in cycles |

## Message and scheduling paths

`Turn.io → HMAC verified webhook → participant state and database → OutboundMessage → deliver_outbound → Turn.io`

`Daily run_checkins → WeeklyCheckIn and review alerts → approved template in OutboundMessage → deliver_outbound`

The webhook verifies the raw request bytes with Turn's base64 HMAC SHA-256 signature. It processes text and interactive replies for the `whatsapp` subscription, persists the unique Turn message ID and queues a reply in the same database transaction. Duplicate inbound IDs do not create extra check-ins or replies. It returns before any outbound network request. The separate worker attempts accepted messages, applies a capped retry delay and leaves failures visible to administrators. External gateway acceptance is not proof of handset delivery. After an uncertain provider success and a process crash, duplicate outbound delivery is possible.

Weekly cycles use Monday as the beginning of a week in the Django Africa/Nairobi timezone. A week containing a recorded mood is complete; older weeks without one are marked missed. Two most recently closed missed cycles yield one open human review alert. Monday reminders require explicit consent, a WhatsApp ID and an approved template configured in the environment. Withdrawal of consent cancels queued proactive reminders at send time. Session confirmations use text within a recent conversation or an approved one-parameter template outside it.

The immediate rule flags a sudden mood drop, three low scores, or configured keyword matches. Tier 1 keywords create a high priority review alert and use a safety response. The optional `care/model_ports.py` adapters have no implementation in this repository. Classifier results, if later available, can populate `MoodEntry`; a conversational model can replace the fallback note reply after separate evaluation. Model output does not replace the human review queue. No untrained scores, inferred diagnoses, or two-of-three classifier consensus are claimed.

## Operational decisions before live use

- Arrange consent and age policy, local escalation and staffing with qualified supervisors and counsellors.
- Use PostgreSQL, HTTPS, secure secrets, audited access, encryption, backups and data retention controls for sender IDs and notes.
- Monitor failed outbound messages and open alerts with a tested on-call response; a dashboard alone does not notify someone.
- Verify actual Turn credentials, webhook registration, templates and WhatsApp behavior with authorized test contacts.

Turn references: https://whatsapp.turn.io/docs/api/webhooks and https://whatsapp.turn.io/docs/api/messages
