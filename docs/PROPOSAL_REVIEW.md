# Proposal comparison

Source: `JadaWalubiri_162903_EmannuelOlang'.pdf`, uploaded 15 July 2026, especially sections 2.5.5–2.6 and 3.5–3.6. Reviewed against the application on 1 October 2026. This compares implementation with the proposal; it does not claim live service approval or model evaluation.

| Proposal requirement | Previous gap | Current implementation / limit |
| --- | --- | --- |
| WhatsApp-only participant experience | Web mockup could look like the actual participant UI | Clearly labelled staff-only development simulator; participants use normal WhatsApp |
| Nickname and age onboarding | Only consent and mood prompts | Nickname and validated age 13–24, persisted onboarding state |
| Plain-language flow for under-18s | No age-dependent step | Additional understanding/agreement step before completing onboarding; records assent, not guardian permission |
| Round-robin counsellor assignment | Manual assignment only | Locked rotation among explicitly eligible, active counsellor profiles; existing assignment preserved |
| No counsellor available | Could silently remain unassigned | Waiting list in admin and action to assign after profiles become available |
| Mixed English/Kiswahili prompts | Mostly English | Short mixed-language mood and booking prompts; model adaptation remains separate |
| Weekly check-ins and missed engagement | Missed moods ignored other contact | Weekly cycle; two missed weeks flag only when there were no other inbound messages in those weeks |
| Three low consecutive weekly check-ins | Any three mood records, even the same day | Distinct consecutive weeks required; uses the latest score in each week |
| Sudden drop of three points | Generic medium alert | Explicit high-priority sudden-drop review |
| Seven-day hybrid agreement | Single keyword could independently flag | Persisted distinct-layer evidence, seven-day window, threshold setting 0.85; no fabricated classifier signal |
| Tier-1 override | Basic keyword alert | Immediate high-priority alert with support guidance, also for text sent while choosing slots |
| Counsellor alerts and escalation | Dashboard records only | Staff template queue, opt-in contacts, high-priority ordering, 24-hour escalation log and admin overdue list |
| Support after overdue alert | Missing | Recent-window text or approved support template; deployment/settings needed for delivery |
| Participant selects time in WhatsApp | Staff-only manual booking | Numbered available slots from assigned counsellor, persistent choices, transactional booking and stale-slot handling |
| Manage counsellor availability | Missing | Availability page; staff can create slots for another counsellor; 30-minute overlap checks |
| Session confirmations to both parties | Participant confirmation only | Participant confirmation plus staff template notice when configured; recorded booking is visible without Turn |
| Pending requests in counsellor workspace | Admin-only request list | Assigned-counsellor pending request list, also visible to staff |
| Complete/cancel sessions | Admin record edit only | Explicit session actions; cancellation stops a pending confirmation |
| Four-week mood history | Most recent records regardless of time | Four-week profile chart and check-in history |
| Feedback on true/false positives | Only mark reviewed | Confirmed concern / false positive / follow-up outcome and optional note with reviewer/time |
| See alert reason and source | Combined under ambiguous Signal header | Separate Reason and Trigger source columns |
| Review participant free text | Latest mood note only | Recent message history and available classifier results in profile |
| Twelve-month retention and deletion within thirty days | No maintenance path | Scheduled purge command; deletion request through chat pauses check-ins; daily worker deletes due profiles on day 30 |
| Model integration | Placeholder only | Still pending, intentionally; ports and recent conversation context are prepared |
| Complete local journey testing | Scripted browser state only | Staff-only simulator calls the real handler and saves DEMO records; provider queue stays empty |

## Explicit interpretations and remaining dependencies

- Section 2.5.5 specifies standalone low-weekly-mood, sudden-drop, disengagement and Tier-1 review flags; sections 2.5.6 and 3.6.3 specify two-layer agreement generally. The implementation retains those named standalone exceptions and applies two-layer agreement to other combinations. This interpretation should be confirmed during supervisor review.
- The proposal names Bootstrap and Chart.js. The current CSS and canvas chart provide the required screens and four-week trend without adding network/CDN dependencies. Their visual behavior is equivalent for this prototype; the library choice is a documented implementation difference.
- The separate conversational model currently being trained is not the proposal's sentiment classifier. Both adapters still require evaluated artifacts and integration. This change does not claim a trained classifier or evaluated conversational safety.
- Minor assent is not proof of guardian consent or approval to enroll real minors. The operational consent policy and staffed safeguarding process remain prerequisites for live use.
- Queued staff messages require an approved template and explicit contact opt-in. Missing settings leave the dashboard as the visible review path. Configured settings do not prove gateway delivery.
- General emergency contacts in the support text are Kenya emergency lines 999/112, verified against the National Police Service [service standards](https://nationalpolice.go.ke/sites/default/files/2025-07/NPS%20poster%20-%20SERVICE%20STANDARDS_0.pdf). They are not represented as specialist counselling lines. Approve the corresponding support template separately.
- Run retention daily; the command selects deletion requests at least 29 days old so the next daily run occurs within the promised thirty-day maximum. Mood/message content older than twelve calendar months is purged, not archived with identifiers.
- Deployment, Turn account/template approval, monitored workers, staff coverage, backups, encryption and supervised acceptance testing remain external readiness work. Local tests use fictional data and mocked gateway calls.
