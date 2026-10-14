# Review the full application

## Update the existing Windows checkout

Stop Django with Ctrl+C and enter the correct folder:

```powershell
cd C:\Users\jadaw\OneDrive\MINDBRIDGE\mindbridge
git status -sb
```

Continue only if you are on `feat/full-stack-care-workspace` with no unrelated local edits:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DJANGO_DEBUG = "1"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py prepare_test_data
.\.venv\Scripts\python.exe manage.py runserver
```

Keep PowerShell open. Log in at http://127.0.0.1:8000/login/ with your existing superuser account. Create a superuser only if one does not exist; reset a known account password with `manage.py changepassword USERNAME` if needed.

## Prepared testing workspace

Run `prepare_test_data` once after migrations, with `DJANGO_DEBUG=1`. It creates three fictional counsellors with separate logins, six named participants, the categorized keyword library and future appointment slots. Save the passwords printed in PowerShell. No fixed passwords are committed, and rerunning the command does not reset passwords or undo alert reviews. Use `manage.py changepassword USERNAME` if you lose a test password.

| Counsellor | Username | Initially assigned participants |
| --- | --- | --- |
| Amina Otieno | `amina.otieno` | Kelvin Otieno, Peter Kamau |
| Brian Mwangi | `brian.mwangi` | Dennis Mwangi, Daniel Mutua |
| Grace Wanjiru | `grace.wanjiru` | Samuel Ochieng, Hassan Ali |

All names and records are fictional. Counsellors are active ordinary users, not staff/superusers. Test profiles receive local simulator assignments and are excluded from automatic live-participant assignment. No phone numbers or WhatsApp notification opt-ins are added. Use your existing superuser to view the administrator screens.

There are six appointment slots per counsellor: tomorrow and the next two days at 10:00 and 14:00 EAT. Samuel has one scheduled appointment; Daniel has a pending request. Details and expected alerts are in [TEST_DATA.md](TEST_DATA.md). You can add further times through **Counsellor availability** as administrator or **My availability** as counsellor; an administrator must choose a counsellor, while ordinary counsellors only manage their own times.

## Review the participant journey

Open http://127.0.0.1:8000/preview/whatsapp/ while signed in as staff. This simulator requires development mode.

1. Click **Start a new conversation**.
2. Choose **I agree**.
3. Enter a nickname, such as `Kevin Kamau`.
4. Enter age `19`. In another demo use `16` to inspect the additional agreement step.
5. Submit mood `3`, then write a fictional note.
6. Choose **Counsellor**. The chat offers available times for the assigned counsellor.
7. Reply `1` to select the first appointment. The chat should confirm the date/time.
8. Click **Open participant profile** to inspect assignment, mood and messages.
9. Open Sessions and confirm the booking.

The simulator saves `MB-CHAT-*` records in the local database, but never creates outbound provider messages. Refresh dashboard pages to see updates. You do not need to connect a model or Turn account for this review.

If there are no available times, the chat records a pending request instead. The assigned counsellor's overview lists that request. The administrator sees the aggregate pending count. Add a slot as administrator, or sign in as the assigned counsellor to use **Schedule session**.

## Review counsellor and administrator controls

- **Alerts**: Reason and Trigger source are separate columns; keyword alerts also show the matched phrases. Save an outcome and optional review note; verify it under Reviewed.
- **Participant profile**: the **Book counselling session +** button is at the top; inspect four-week moods and recent messages.
- **Sessions**: mark a fictional appointment completed or cancelled. Cancellations stop any pending booking confirmation.
- **My availability**: add or remove future times. Overlaps are rejected. Booked times cannot be removed directly.
- **Admin dashboard**: monitor total participants, open alerts, pending request counts, review completion, assignment waiting list, overdue alerts, deletion requests and template/queue readiness. Create counsellor accounts and profiles, maintain keywords and set initial availability.
- **Django admin**: manage counsellor accounts, eligibility, participant assignments and keywords. Case records (moods, alerts, sessions, requests and messages) are read-only, including for the superuser. Create/remove slots through the validated availability UI.

Administrators land on the administration dashboard after login and cannot open counsellor case pages or submit review, booking or session-status actions. This follows proposal sections 3.6.4, 3.6.6 and 3.6.7: admins oversee overdue follow-up; assigned counsellors review cases and manage sessions. The WhatsApp simulator remains a DEBUG-only testing tool and is not a live admin conversation channel.

Use a private browser window to sign in as the counsellor. They should see only assigned participants and their associated requests, alerts and sessions, and cannot access staff administration or the simulator.

Existing `DEMO-001`–`DEMO-003` sample participants are renamed in place to `MB-1001`–`MB-1003`, preserving their identity and related records. Existing simulator codes become `MB-CHAT-*`; user-entered nicknames are preserved. The older `seed_demo` command remains an alias. Real accounts and real participant records are not modified.

## What still needs the live connection

Real participants use the MindBridge WhatsApp number. Configure HTTPS, PostgreSQL, Turn credentials, approved templates and scheduled workers using the [Turn integration guide](TURN_INTEGRATION.md). Test acceptance on authorized Turn test contacts. Model-generated responses appear only after the evaluated inference adapters are connected.
