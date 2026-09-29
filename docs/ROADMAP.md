# Development milestones

## 1. Reviewable UI and core flow

- [x] Django project, migrations, sample data, and sign-in
- [x] Counsellor overview, participant profiles, mood history, alerts, and sessions
- [x] Administrator dashboard and account/keyword management through Django admin
- [x] WhatsApp flow preview and signed Turn.io webhook
- [x] Outbound queue, retries, weekly schedule and missed check-in alerts
- [x] Interactive consent buttons and session confirmation routing
- [x] Access, webhook, queue and schedule tests

## 2. Model integration

- [ ] Freeze dataset versions and approved label definitions
- [ ] Evaluate English, Kiswahili, Sheng and code-switched slices
- [ ] Load the approved inference artifact behind a local service interface
- [ ] Validate confidence thresholds and the hybrid review policy with supervisors

## 3. Pilot readiness

- [ ] Connect a test Turn.io number and validate real inbound/outbound delivery
- [ ] Validate templates, real webhook and worker with a Turn.io test number
- [ ] Add staff notifications, automatic assignment policy, and response-time monitoring
- [ ] Finalize consent, retention, deletion, encryption, access audit, and safeguarding procedures
- [ ] Conduct supervised usability and security testing before any real pilot
