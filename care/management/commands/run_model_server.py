"""Run the MindBridge private conversational model service (FastAPI/uvicorn)."""
import os
import subprocess
import sys
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the MindBridge private conversational model service (FastAPI/uvicorn)."

    def add_arguments(self, parser):
        parser.add_argument("--port", type=int, default=8001, help="Port to bind (default: 8001)")
        parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")

    def handle(self, *args, **options):
        port = options["port"]
        host = options["host"]
        self.stdout.write(self.style.SUCCESS(
            f"Starting MindBridge conversational model service at http://{host}:{port}..."
        ))
        cmd = [sys.executable, "-m", "uvicorn", "model_server.app:app", "--host", host, "--port", str(port)]
        env = os.environ.copy()
        env.setdefault("MINDBRIDGE_ALLOW_SUPERVISED", "1")
        try:
            subprocess.run(cmd, env=env)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nModel service stopped."))
