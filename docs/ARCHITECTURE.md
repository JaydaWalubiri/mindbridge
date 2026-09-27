# Architecture

| User | Interface | Current implementation |
| --- | --- | --- |
| Participant | WhatsApp via Turn.io | Opt-in, mood check-in, note, session request, pause and help |
| Counsellor | Django template pages | Assigned participants, mood history, alerts, sessions |
| Administrator | Dashboard and Django admin | Account management, assignments, keyword library, request queue |

## Message path

`Turn.io → signed webhook → participant lookup → scripted state → database → Turn.io reply`

Turn's `X-Turn-Hook-Signature` is checked against the original request bytes with HMAC SHA-256. Only the `whatsapp` subscription and text messages are processed. The external message ID is unique in the database, preventing a repeated webhook from creating a second check-in. When reply delivery fails, the saved reply can be retried on webhook redelivery.

The immediate review rule detects a sudden mood drop, three low scores, and administrator configured keyword matches. It emits a review alert. The trained model and a validated hybrid decision are not yet connected; integrate them in `care/services.py` only after evaluation, review and approval. The dashboard makes no diagnosis and does not automatically decide a participant's care.

## Security and data decisions still needed

- Document consent and age handling, appropriate retention, deletion, and escalation with a qualified project supervisor and counsellors.
- Protect sender identifiers and free text at rest, limit staff permissions, log access, and audit any exports.
- Configure a real notification path for staff and a tested response process before receiving live messages.
- Add scheduled prompts and messaging templates according to Turn.io and WhatsApp rules after integration testing.

Turn references: https://whatsapp.turn.io/docs/api/webhooks and https://whatsapp.turn.io/docs/api/messages
