from django.core.management.base import BaseCommand
from care.services import deliver_due


class Command(BaseCommand):
    help = "Send queued Turn.io messages. Schedule once a minute in production."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        self.stdout.write(f"Accepted {deliver_due(max(1, min(options['limit'], 500)))} messages")
