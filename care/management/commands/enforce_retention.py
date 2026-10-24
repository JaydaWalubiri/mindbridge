from django.core.management.base import BaseCommand
from care.workflows import enforce_retention


class Command(BaseCommand):
    help = "Purge mood/message records older than 12 months and profiles whose deletion request is 30 days old."
    def handle(self, *args, **options):
        moods, profiles = enforce_retention()
        self.stdout.write(f"Purged {moods} mood records; deleted {profiles} requested profiles.")
