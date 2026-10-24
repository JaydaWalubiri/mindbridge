from django.core.management.base import BaseCommand
from care.services import run_weekly_checkins


class Command(BaseCommand):
    help = "Update weekly check-ins, missed alerts and queue approved template reminders. Run daily."

    def handle(self, *args, **options):
        created, missed = run_weekly_checkins()
        self.stdout.write(f"Created {created} cycles; closed {missed} missed cycles")
