from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from care.model_ports import _load_model, classify_note


class Command(BaseCommand):
    help = "Download the configured sentiment model or check local inference with fictional text."

    def add_arguments(self, parser):
        parser.add_argument("--download", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(f"Model: {settings.SENTIMENT_MODEL}@{settings.SENTIMENT_REVISION}")
        if options["download"]:
            if _load_model(settings.SENTIMENT_MODEL, settings.SENTIMENT_REVISION, True) is None:
                raise CommandError("Unable to download/load model. Check dependencies and internet access.")
            _load_model.cache_clear()
            self.stdout.write(self.style.SUCCESS("Model downloaded. Chat requests use the local cache only."))
        if not settings.SENTIMENT_ENABLED:
            if options["download"]:
                return
            raise CommandError("Set SENTIMENT_ENABLED=1 to check inference.")
        for text in ("I feel happy and supported.", "I feel miserable and upset."):
            result = classify_note(text)
            if result is None:
                raise CommandError("No prediction. Download model first; check logs and restart after setup.")
            self.stdout.write(f"{text} -> {result.label} ({result.confidence:.4f})")
        self.stdout.write(f"Sentiment contributes to risk: {settings.SENTIMENT_RISK_ENABLED}")
        self.stdout.write("These are smoke checks, not clinical or multilingual evaluation.")
