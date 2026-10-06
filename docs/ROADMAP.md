# Project roadmap

The first application build is in [PR #1](https://github.com/JaydaWalubiri/mindbridge/pull/1). It includes onboarding, counsellor assignment, mood tracking, alerts, booking, admin controls and a local WhatsApp simulator. Review and acceptance are still needed.

The following milestones and issues are tracked on GitHub. No due dates have been set.

## 1. [Core workflows and UI](https://github.com/JaydaWalubiri/mindbridge/milestone/1)

| Issue | Completion requirements |
| --- | --- |
| [#2: Organize the GitHub repository](https://github.com/JaydaWalubiri/mindbridge/issues/2) | Short README; clear backend/frontend map; contribution guide and templates; issues and milestones created; default `main` and branch settings verified. |
| [#3: Review participant, counsellor and admin journeys](https://github.com/JaydaWalubiri/mindbridge/issues/3) | Walk through onboarding, assignment, check-ins, alerts and booking with fictional data; record screenshots and any bugs; verify role access; review PR #1 before merging. |
| [#14: Improve keyword matching and verify risk rules](https://github.com/JaydaWalubiri/mindbridge/issues/14) | Direct negation and explicit phrase variants; current-signal requirement; controlled-date mood and disengagement tests; results and limits in [RISK_CHECKS.md](RISK_CHECKS.md). |

## 2. [Model integration](https://github.com/JaydaWalubiri/mindbridge/milestone/2)

| Issue | Completion requirements |
| --- | --- |
| [#4: Connect the trained conversation model](https://github.com/JaydaWalubiri/mindbridge/issues/4) | Record the model version; implement `generate_response`; test English, Kiswahili and Sheng examples and model failure fallback. |
| [#5: Connect the sentiment classifier](https://github.com/JaydaWalubiri/mindbridge/issues/5) | Implement `classify_note`; store scores and sources; check rule/keyword agreement, Tier-1 override and configured thresholds. |
| [#6: Evaluate model performance](https://github.com/JaydaWalubiri/mindbridge/issues/6) | Use held-out English, Kiswahili, Sheng and code-switched examples; record the split, labels, metrics and language differences; document the selected threshold. |

## 3. [Live WhatsApp integration](https://github.com/JaydaWalubiri/mindbridge/milestone/4)

| Issue | Completion requirements |
| --- | --- |
| [#7: Test the Turn.io connection](https://github.com/JaydaWalubiri/mindbridge/issues/7) | Configure authorized test contacts, signed webhook and approved templates; verify onboarding, replies, booking and staff notices on actual WhatsApp; record delivery failures and retries. |
| [#8: Set up scheduled tasks](https://github.com/JaydaWalubiri/mindbridge/issues/8) | Schedule outbound delivery, check-ins, escalation and retention commands; verify execution, failures and monitoring. |

## 4. [Evaluation and deployment](https://github.com/JaydaWalubiri/mindbridge/milestone/3)

| Issue | Completion requirements |
| --- | --- |
| [#9: Deploy Django with PostgreSQL](https://github.com/JaydaWalubiri/mindbridge/issues/9) | Configure HTTPS, environment settings and PostgreSQL; run migrations and deployment checks; verify access and a backup/restore exercise. |
| [#10: Confirm consent and data handling](https://github.com/JaydaWalubiri/mindbridge/issues/10) | Document the approved consent and safeguarding arrangements; confirm retention/deletion across the app, provider and backups. |
| [#11: Complete user testing and project handover](https://github.com/JaydaWalubiri/mindbridge/issues/11) | Record usability findings with authorized testers; fix identified issues; update setup and system notes; prepare an accepted release tag and demonstration. |

Use each issue checklist to determine completion. Search existing issues before creating duplicates. Keep unfinished tasks open. Do not mark model or live WhatsApp work complete based on the local simulator.
