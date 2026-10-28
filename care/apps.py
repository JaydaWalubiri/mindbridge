import os
import sys
import threading
from django.apps import AppConfig


class CareConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "care"

    def ready(self):
        # Pre-warm local sentiment model in a background thread during runserver
        # so the very first conversational message does not wait 5-8s for cold loading.
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") == "true":
            from django.conf import settings
            if getattr(settings, "SENTIMENT_ENABLED", False):
                def _warm():
                    try:
                        from .model_ports import classify_note
                        classify_note("Warm up sentiment classifier.")
                    except Exception:
                        pass
                threading.Thread(target=_warm, daemon=True, name="sentiment-warmup").start()
