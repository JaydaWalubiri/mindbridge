# Risk checks

## Current behaviour

The conversation model generates replies. A separate sentiment classifier must
return a label and confidence. Neither adapter is connected yet; the tests use
explicit mock predictions rather than claiming model performance.

| Signal | Behaviour |
| --- | --- |
| Tier 1 keyword | Immediate high-priority review alert, independent of sentiment |
| Three low weekly moods | Latest mood in each of three consecutive calendar weeks is at most 2; latest entry must be within seven days; medium review alert |
| Sudden drop | Latest two mood scores fall by at least three points; latest entry must be within seven days; high-priority review alert |
| Disengagement | Two closed weekly cycles without moods and without other inbound contact across those cycles; medium welfare alert |
| Other combinations | At least two distinct layers of evidence within seven days, with a risk signal in the current assessment |
| Sentiment evidence | `negative` at confidence at least `RISK_NEGATIVE_THRESHOLD` (default 0.85) |

The named mood/disengagement exceptions are retained from the proposal
interpretation in [PROPOSAL_REVIEW.md](PROPOSAL_REVIEW.md). Multiple keyword
matches count as one layer. Alerts are requests for human review, not diagnoses.
Missed check-ins require the daily `run_checkins` task; scheduling remains open.

## Keyword matching

Matching uses active library entries, whole phrase boundaries, Unicode and case
normalisation, repeated whitespace and hyphen normalisation. Explicit English
variants include `wanna die`, `want 2 die`, `want to kill my self`, and `feeling
hopeless`. No fuzzy matching is used for urgent phrases.

Direct English negation immediately before supported predicates is excluded:
`I don't want to die` and `I am not feeling hopeless` do not create keyword
evidence. Ambiguous wording such as `I am not sure if I want to die` still reaches
review. If a later affirmative match occurs, it is retained. A custom phrase
such as `don't want to live` is matched literally when configured.

This is a limited rule, not general language understanding. Reported speech,
sarcasm, indirect negation, unlisted spelling errors and Sheng variations still
need locally reviewed examples and evaluation. The keyword language field is
metadata; all active terms are checked against messages, including code-switching.
Suppressed keyword matches do not suppress independent mood or sentiment signals.

## Verification

All 55 tests passed locally on 6 October 2026 (27 new risk checks). No database
migrations were needed. Tracked in [issue #14](https://github.com/JaydaWalubiri/mindbridge/issues/14).

Run `python manage.py test`. `care/test_risk.py` checks keyword variants and
negation, rule boundaries, distinct weeks, latest weekly score, stale histories,
inactive terms, alert deduplication, sentiment threshold, expired evidence,
neutral messages after old signals, and missed-week/contact exceptions.

On 6 October 2026, the user verified the local simulator journey: onboarding,
assignment, mood and message visibility, urgent keyword alert, saved review,
participant booking, counsellor appointment visibility and completion. This
does not verify live Turn.io delivery or model evaluation.

For a quick local keyword check, load `python manage.py add_keywords`, complete
onboarding in the staff-only WhatsApp preview, and send fictional test text.
`I don't want to die` should not create keyword evidence; `nataka kujiua` should
create a Tier 1 alert when its active entry is present. Check the assigned
counsellor's Alerts page. Existing independent mood evidence may still alert.

Remaining work: reviewed multilingual dictionary, labelled risk evaluation,
actual classifier integration, scheduled workers and live WhatsApp acceptance.
