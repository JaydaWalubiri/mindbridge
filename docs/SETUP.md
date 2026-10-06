# Local setup


From the `mindbridge` folder:

```powershell
# First setup only:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Each new PowerShell session:
$env:DJANGO_DEBUG = "1"
.\.venv\Scripts\python.exe manage.py migrate
# First setup only: create an administrator account.
.\.venv\Scripts\python.exe manage.py createsuperuser
# Optional: clearly fictional records and a demo counsellor profile.
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py runserver
```

For an existing checkout, stop Django, run `git status -sb` and then `git pull --ff-only` if your working tree is clean; reinstall requirements and run migrations before restarting. See the review guide for account and participant steps. No account passwords are shipped.

macOS/Linux: use `python -m venv .venv`, `source .venv/bin/activate`, `pip install -r requirements.txt`, `export DJANGO_DEBUG=1`, then the same `python manage.py ...` commands.

| Screen | Local URL |
| --- | --- |
| Login | http://127.0.0.1:8000/login/ |
| Counsellor overview and requests | http://127.0.0.1:8000/ |
| Alerts and review feedback | http://127.0.0.1:8000/alerts/ |
| Participants and profiles | http://127.0.0.1:8000/participants/ |
| Appointments | http://127.0.0.1:8000/sessions/ |
| Counsellor availability | http://127.0.0.1:8000/availability/ |
| Administrator operations | http://127.0.0.1:8000/workspace-admin/ |
| Django record management | http://127.0.0.1:8000/admin/ |
| Staff-only local participant simulator | http://127.0.0.1:8000/preview/whatsapp/ |
