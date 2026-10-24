from django.core.management.base import BaseCommand
from care.workflows import run_escalations


class Command(BaseCommand):
    help = "Escalate unreviewed alerts after 24 hours; queue allowed notifications."
    def handle(self, *args, **options):
        count = run_escalations()
        self.stdout.write(f"Escalated {count} alerts.")
