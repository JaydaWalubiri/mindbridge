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
.\.venv\Scripts\python.exe manage.py runserver
```

Keep PowerShell open. Log in at http://127.0.0.1:8000/login/ with your existing superuser account. Create a superuser only if one does not exist; reset a known account password with `manage.py changepassword USERNAME` if needed.

## Set up a counsellor to receive the demo participant

1. In Django admin, create a counsellor user account (Active enabled; Staff and Superuser disabled).
2. Open **Counsellor profiles**, add that user, and enable **Accepts assignments**. You may also give your existing administrator account a profile if you want it to act as a demo counsellor. Ordinary administrators are not automatically assignment candidates.
3. Leave WhatsApp notification opt-in disabled for local review; no actual phone number is needed.
4. Open **My availability** in the web workspace. An administrator can select the counsellor in the form; an ordinary counsellor can only manage their own times.
5. Add two future appointment times. Each is thirty minutes. All displayed times are EAT.

## Review the participant journey

Open http://127.0.0.1:8000/preview/whatsapp/ while signed in as staff. This simulator requires development mode.

1. Click **Start another demo participant**.
2. Choose **I agree**.
3. Enter a nickname, such as `Demo Brian`.
4. Enter age `19`. In another demo use `16` to inspect the additional agreement step.
5. Submit mood `3`, then write a fictional note.
6. Choose **Counsellor**. The chat offers available times for the assigned counsellor.
7. Reply `1` to select the first appointment. The chat should confirm the date/time.
8. Click **Open demo participant profile** to inspect assignment, mood and messages.
9. Open Sessions and confirm the booking.

The simulator saves `DEMO-CHAT-*` records in the local database, but never creates outbound provider messages. Refresh dashboard pages to see updates. You do not need to connect a model or Turn account for this review.

If there are no available times, the chat records a pending request instead. The assigned counsellor's overview lists that request. The administrator sees it too. Add a slot or use the **Schedule session** button to arrange it manually.

## Review counsellor and administrator controls

- **Alerts**: Reason and Trigger source are separate columns. Save an outcome and optional review note; verify it under Reviewed.
- **Participant profile**: the **Book counselling session +** button is at the top; inspect four-week moods and recent messages.
- **Sessions**: mark a fictional appointment completed or cancelled. Cancellations stop any pending booking confirmation.
- **My availability**: add or remove future times. Overlaps are rejected. Booked times cannot be removed directly.
- **Admin dashboard**: inspect pending requests, assignment waiting list, overdue alerts, deletion requests and template/queue readiness.
- **Django admin**: manage users, counsellor eligibility, keyword settings and operational records. Appointment slots are inspected here; create/remove them through the validated availability UI.

Use a private browser window to sign in as the counsellor. They should see only assigned participants and their associated requests, alerts and sessions, and cannot access staff administration or the simulator.

For optional sample records, stop Django and run `manage.py seed_demo`, then restart. The seed command creates fictional dashboard records and a profile for the first superuser; it does not create a password.

## What still needs the live connection

Real participants use the MindBridge WhatsApp number. Configure HTTPS, PostgreSQL, Turn credentials, approved templates and scheduled workers using the README. Test acceptance on authorized Turn test contacts. Model-generated responses appear only after the evaluated inference adapters are connected.
