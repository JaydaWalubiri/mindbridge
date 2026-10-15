# Architecture

| Actor | Interface | Responsibilities |
| --- | --- | --- |
| Participant | Normal WhatsApp through Turn.io | Consent, nickname/age, mood and free text, appointment selection, pause/deletion |
| Counsellor | Django workspace | Assigned participants, requests, availability, alerts with feedback, appointments |
| Administrator | Custom operations page and Django admin | Staff accounts/profiles, waiting assignments, overdue cases, keywords and delivery status |

## Incoming messages and replies

Turn sends a signed webhook. Django verifies the raw body with base64 HMAC SHA-256, handles text or interactive choices, locks the participant state, stores the unique message ID, applies the shared conversation workflow and queues its reply. The webhook performs no outbound provider request. Duplicate IDs do not create another check-in or booking.

`deliver_outbound` processes due queue records and retries failures with bounded backoff. It rechecks participant consent, simulation status and staff notification opt-in before sending. Provider acceptance is recorded separately from any claim of handset delivery. Ambiguous provider success followed by a worker crash can still cause duplicate delivery.

The local simulator requires staff sign-in, CSRF-protected POST requests and development mode. It runs the same handler with an explicitly simulated participant. All outbound queue functions skip simulated people. The simulator is not a participant portal or a deployed WhatsApp connection.

## Assignment and appointments

Eligible active counsellor profiles participate in round-robin allocation. A database-seeded singleton cursor is locked while advancing. Completed onboarding preserves an existing counsellor; no eligible candidate leaves a visible waiting assignment.

Appointment slots are thirty minutes. Participants receive at most five numbered available times for their counsellor; slot IDs are persisted so a numeric reply selects the displayed option. Booking locks the counsellor and selected slot, checks active/future availability and rejects overlaps or a slot already taken. Staff can book from the profile. Confirmations are queued for participants and opted-in staff when provider settings permit them.

## Risk and human review

`care/risk.py` stores distinct-layer evidence within a seven-day window. The classifier port remains empty until integrated. Configured Tier-1 terms, a sudden three-point drop, three low consecutive weekly mood scores and two missed/no-contact weekly cycles have explicit review paths. Other combinations need evidence from at least two distinct layers; negative classification uses the configurable 0.85 threshold.

Alerts are ordered high before medium priority. Review captures outcome, optional note, staff identity and time. An independent worker marks still-open alerts as escalated after twenty-four hours, exposes them in admin and queues approved staff/support notifications where configured. The dashboard is a human review tool, not an emergency response guarantee.

## Data lifecycle

PostgreSQL is the production database; SQLite supports local review. Mood and message content is purged after twelve calendar months, including associated old queue/evidence/alert content. Participants can request profile deletion in chat, which pauses check-ins. Daily maintenance purges due requested profiles and cascades linked records within thirty days. Provider-side copies, backups and encryption must also be covered by deployment policy.

## Model integration

`care/model_ports.py` defines the classifier and response interfaces. The response adapter receives recent interaction context. Classification results can populate both note and inbound message records. A missing adapter returns no invented model result; the application uses scripted fallback text and configured review rules.
