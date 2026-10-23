"""One supervised worker process for delivery and scheduled care workflows."""
import time
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, close_old_connections
from django.utils import timezone
from care.models import WorkerStatus
from care.services import deliver_due, run_session_reminders, run_weekly_checkins
from care.workflows import run_escalations, enforce_retention

TASKS = (("delivery", 60, deliver_due), ("reminders", 300, run_session_reminders),
         ("checkins", 86400, run_weekly_checkins),
         ("escalations", 900, run_escalations), ("retention", 86400, enforce_retention))


class Command(BaseCommand):
    help = "Run one care worker; --once executes all jobs once for local checks."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        if not options["once"] and connection.vendor != "postgresql":
            raise CommandError("Continuous workers require PostgreSQL. Use --once for local testing.")
        deadlines = {}
        while True:
            if not connection.in_atomic_block:
                close_old_connections()
            now = time.monotonic()
            failures = []
            for name, interval, action in TASKS:
                if now < deadlines.get(name, 0):
                    continue
                status, _ = WorkerStatus.objects.get_or_create(task=name)
                status.last_attempt_at = timezone.now()
                status.save(update_fields=["last_attempt_at"])
                try:
                    action()
                    status.last_success_at = timezone.now()
                    status.last_error_type = ""
                except Exception as error:
                    # Provider exceptions can contain private text; record type only.
                    status.last_error_type = type(error).__name__[:64]
                    failures.append(name)
                    self.stderr.write(f"{name}: failed ({status.last_error_type})")
                else:
                    self.stdout.write(f"{name}: completed")
                status.save(update_fields=["last_success_at", "last_error_type"])
                deadlines[name] = now + (60 if status.last_error_type else interval)
            if options["once"]:
                if failures:
                    raise CommandError("Failed jobs: " + ", ".join(failures))
                return
            time.sleep(60)
