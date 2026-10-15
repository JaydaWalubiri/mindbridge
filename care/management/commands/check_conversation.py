"""Check the private endpoint using fictional text, never participant records."""
import json
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from care.model_ports import _NoRedirect, generate_response
from care.response_policy import route


class Command(BaseCommand):
    help = "Check the configured private conversation endpoint with fictional examples."

    def handle(self, *args, **options):
        if not settings.CONVERSATION_ENABLED or not settings.CONVERSATION_API_TOKEN:
            raise CommandError("Set CONVERSATION_ENABLED and the separate service API token first.")
        parsed = urlsplit(settings.CONVERSATION_URL)
        if (not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query
                or parsed.path != "/v1/reply" or not (parsed.scheme == "https" or
                    (settings.DEBUG and parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}))):
            raise CommandError("Use a trusted HTTPS /v1/reply URL, or loopback HTTP in development.")
        request = Request(settings.CONVERSATION_URL.removesuffix("/v1/reply") + "/health",
            headers={"Authorization": "Bearer " + settings.CONVERSATION_API_TOKEN})
        try:
            with build_opener(_NoRedirect()).open(request, timeout=settings.CONVERSATION_TIMEOUT) as response:
                raw = response.read(16385)
            if len(raw) > 16384:
                raise ValueError("Oversized response")
            health = json.loads(raw)
            if not isinstance(health, dict) or health.get("status") != "ready_for_supervised_testing":
                raise ValueError("Endpoint is not ready")
            if health.get("model_source") != settings.CONVERSATION_EXPECTED_SOURCE:
                raise ValueError("Unexpected adapter revision")
        except (OSError, ValueError):
            raise CommandError("Private model health check failed; check host, credentials and startup.") from None
        self.stdout.write("Authenticated endpoint ready for supervised testing; clinical approval is not asserted.")
        for language, text in (("English", "I feel worried about a school presentation."),
                               ("Kiswahili", "Nina wasiwasi kuhusu kuzungumza darasani."),
                               ("Sheng", "Niko na pressure ya kuongea mbele ya class.")):
            self.stdout.write(f"{language}: {generate_response(text, {'language': language})}")
        assert route("Nataka kujiumiza") == "urgent"
        self.stdout.write("Explicit safety messages use scripted guidance and independent alerts, not generation.")
