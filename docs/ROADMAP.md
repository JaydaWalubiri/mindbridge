# Project roadmap

The first application build is in [PR #1](https://github.com/JaydaWalubiri/mindbridge/pull/1). It includes onboarding, counsellor assignment, mood tracking, alerts, booking, admin controls and a local WhatsApp simulator. Review and acceptance are still needed.

The following groups are intended as GitHub milestones. They have not yet been created: the current GitHub connection rejected write access. Until they exist, this page records the exact work to create and track. No due dates have been set.

## 1. Core workflows and UI

| Issue to create | Completion requirements |
| --- | --- |
| Organize the GitHub repository | Short README; clear backend/frontend map; contribution guide and templates; issues and milestones created; default `main` and branch settings verified. |
| Review participant, counsellor and admin journeys | Walk through onboarding, assignment, check-ins, alerts and booking with fictional data; record screenshots and any bugs; verify role access; review PR #1 before merging. |

## 2. Model integration

| Issue to create | Completion requirements |
| --- | --- |
| Connect the trained conversation model | Record the model version; implement `generate_response`; test English, Kiswahili and Sheng examples and model failure fallback. |
| Connect the sentiment classifier | Implement `classify_note`; store scores and sources; check rule/keyword agreement, Tier-1 override and configured thresholds. |
| Evaluate model performance | Use held-out English, Kiswahili, Sheng and code-switched examples; record the split, labels, metrics and language differences; document the selected threshold. |

## 3. Live WhatsApp integration

| Issue to create | Completion requirements |
| --- | --- |
| Test the Turn.io connection | Configure authorized test contacts, signed webhook and approved templates; verify onboarding, replies, booking and staff notices on actual WhatsApp; record delivery failures and retries. |
| Set up scheduled tasks | Schedule outbound delivery, check-ins, escalation and retention commands; verify execution, failures and monitoring. |

## 4. Evaluation and deployment

| Issue to create | Completion requirements |
| --- | --- |
| Deploy Django with PostgreSQL | Configure HTTPS, environment settings and PostgreSQL; run migrations and deployment checks; verify access and a backup/restore exercise. |
| Confirm consent and data handling | Document the approved consent and safeguarding arrangements; confirm retention/deletion across the app, provider and backups. |
| Complete user testing and project handover | Record usability findings with authorized testers; fix identified issues; update setup and system notes; prepare an accepted release tag and demonstration. |

Create one issue for each row, assign its milestone and use its checklist to determine completion. Search existing issues before creating duplicates. Keep unfinished tasks open. Do not mark model or live WhatsApp work complete based on the local simulator.
