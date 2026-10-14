# Prepared application testing data

The names below are realistic fictional identities, not real clients or registered practitioners. Run `manage.py prepare_test_data` with `DJANGO_DEBUG=1` after migrations. The command does not contact Turn or create real WhatsApp recipients.

## Accounts and appointments

Your existing administrator account and password remain unchanged. Three ordinary counsellor accounts are created: `amina.otieno`, `brian.mwangi` and `grace.wanjiru`. Their generated passwords appear only in your terminal on first creation. Reruns preserve passwords, disabled profiles and reviewed alerts. Reset a lost password with `manage.py changepassword USERNAME`.

Each counsellor has slots at 10:00 and 14:00 EAT tomorrow and on the following two days. Slots are 30 minutes long. Existing slot edits and bookings remain intact; rerunning on a later day adds the new future dates.

## Participant scenarios

| Participant | Code | Age / area | Counsellor | Expected result on first preparation |
| --- | --- | --- | --- | --- |
| Kelvin Otieno | MB-1001 | 19 / Kibera | Amina Otieno | High alert: explicit immediate safety phrase; matched phrase shown |
| Dennis Mwangi | MB-1002 | 18 / Mathare | Brian Mwangi | Medium alert: three consecutive weekly moods at 2 or below |
| Samuel Ochieng | MB-1003 | 20 / Mukuru | Grace Wanjiru | High alert: mood drops from 5 to 2; one future session booked |
| Peter Kamau | MB-1004 | 17 / Kibera | Amina Otieno | Medium alert: two consecutive missed weekly check-ins |
| Hassan Ali | MB-1005 | 21 / Mathare | Grace Wanjiru | Positive history, no alert |
| Daniel Mutua | MB-1006 | 16 / Mukuru | Brian Mwangi | Pending counselling request, no alert |

Risk examples use the shared assessment and alert creation functions. Missed-week fixtures use the same missed-check-in rule as the scheduler; they do not run a live provider job. The dataset contains fictional consent and assent timestamps. Test participants remain `is_simulated=True`, and test counsellor profiles carry the same flag, so naming them does not convert them into live records.

Older sample codes are upgraded in place. New local conversations use `MB-CHAT-*`, and their names come from the nickname entered during onboarding. Profiles display **TEST RECORD**. Real records and existing administrator accounts are not renamed. Reviewed alerts remain reviewed when setup is repeated.

## Keyword library and alarm behaviour

The proposed library contains **104 phrases: 32 Tier-1 and 72 Tier-2**, across English, Kiswahili and Sheng/code-switching. Ten categories cover immediate safety, hopelessness, self-worth, isolation, bullying, safety at home, sleep/functioning, school/financial pressure, substance concerns, and loss/emotional distress. Broad warning-sign categories are informed by [NIMH guidance](https://www.nimh.nih.gov/health/publications/warning-signs-of-suicide); the translations, local phrases and tier assignments are project test proposals, not a validated clinical instrument.

- Tier 1: immediate high-priority review, without depending on the sentiment model.
- Sudden drop of 3 or more mood points: high-priority alert.
- Three consecutive low weekly moods: medium-priority alert.
- Two consecutive missed weekly check-ins: medium-priority welfare review.
- Tier 2: one supporting keyword layer. Several phrases still count as one layer; another eligible layer is required for the combined rule. The English sentiment baseline remains excluded by default pending evaluation.

The matcher handles documented spelling variants, word boundaries and selected direct negations. It does not understand every quotation, euphemism or negation. A term such as “stress” or “sad” alone is not an urgent trigger. Existing administrator edits to keyword tiers, languages and active status are preserved. Counsellor and native-language review is required before adopting this list for real participants.

Alerts display **Reason**, **Trigger source**, **Matched phrases** where recorded, **Priority**, and review status. Save an outcome and note to test follow-up. Keyword evidence is traceable without presenting the label as a diagnosis.

## Suggested checks

1. Log in as your administrator; confirm the header is clean and the operational panel appears once in the page body.
2. Inspect administrative counts and read-only records; use the counsellor accounts to review the four prepared alerts, Samuel's session and Daniel's pending request.
3. In a private browser window, sign in as Amina: only Kelvin and Peter should appear. Repeat for the other counsellors.
4. In the administrator's WhatsApp preview, start a new conversation, agree, enter `Kevin Kamau`, age `19`, mood `3` and a note.
5. Confirm a named counsellor is assigned, choose **Counsellor**, select a future slot, and inspect the booked session on that counsellor's dashboard.
6. In another fictional conversation, send `I might hurt myself tonight.` and verify an alert appears with the matched phrase. A supporting concern such as `Masomo yamenilemea` alone should not create a high alarm.

The preview never queues provider messages, even when Turn credentials are present. The live connection and model hosting are the next phase after this local review.
