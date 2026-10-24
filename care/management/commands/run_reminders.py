from django.core.management.base import BaseCommand
from care.services import run_session_reminders


class Command(BaseCommand):
    help = "Scan upcoming sessions and queue automated WhatsApp reminder templates."

    def handle(self, *args, **options):
        queued = run_session_reminders()
        self.stdout.write(f"Queued {queued} session reminder(s)")
