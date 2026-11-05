"""Report configuration and worker evidence without sending WhatsApp messages."""
from datetime import timedelta
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from care.models import CounsellorProfile, Keyword, WorkerStatus
from care.management.commands.run_workers import TASKS


class Command(BaseCommand):
    help = "Inspect whole-system readiness; never sends test messages or prints secrets."

    def add_arguments(self, parser):
        parser.add_argument("--connections", action="store_true", help="Check model inference using fictional text")
        parser.add_argument("--strict", action="store_true", help="Fail if configuration or worker checks fail")

    def handle(self, *args, **options):
        failed = []
        def check(name, okay):
            self.stdout.write(("PASS " if okay else "NEEDS SETUP ") + name)
            if not okay:
                failed.append(name)
        executor = MigrationExecutor(connection)
        check("Database migrations", not executor.migration_plan(executor.loader.graph.leaf_nodes()))
        check("Eligible counsellor", CounsellorProfile.objects.filter(user__is_active=True, accepts_assignments=True).exists())
        check("Active keyword library", Keyword.objects.filter(is_active=True, tier=1).exists())
        check("Green API WhatsApp instance configured", bool(getattr(settings, "GREEN_API_INSTANCE_ID", "")))
        check("Green API WhatsApp token configured", bool(getattr(settings, "GREEN_API_TOKEN_INSTANCE", "")))
        check("Green API WhatsApp host configured", bool(getattr(settings, "GREEN_API_HOST", "")))
        check("Sentiment enabled", settings.SENTIMENT_ENABLED)
        check("Conversation enabled and configured", bool(settings.CONVERSATION_ENABLED and
              settings.CONVERSATION_URL and settings.CONVERSATION_API_TOKEN and settings.CONVERSATION_EXPECTED_SOURCE))
        now = timezone.now()
        for name, interval, _ in TASKS:
            item = WorkerStatus.objects.filter(task=name).first()
            check("Worker " + name, bool(item and not item.last_error_type and item.last_success_at
                  and item.last_success_at >= now - timedelta(seconds=interval + 180)))
        if options["connections"]:
            for command in ("check_sentiment", "check_conversation"):
                try:
                    call_command(command, stdout=self.stdout, stderr=self.stderr)
                except CommandError:
                    check(command, False)
                else:
                    check(command, True)
        self.stdout.write("Settings and heartbeat checks do not prove live WhatsApp delivery, clinical safety or language accuracy.")
        self.stdout.write("Sentiment risk mode: " + ("enabled for explicit evaluation" if settings.SENTIMENT_RISK_ENABLED else "excluded pending evaluation"))
        if options["strict"] and failed:
            raise CommandError("Setup incomplete: " + ", ".join(failed))
