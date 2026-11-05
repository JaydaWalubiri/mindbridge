"""Poll Green API notifications over HTTPS (port 443) so live WhatsApp works even on campus/corporate Wi-Fi that blocks Cloudflare Tunnel (port 7844)."""
import json
import time
import urllib.request
from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Continuously poll Green API receiveNotification over HTTPS (443) and forward events to local green_api_webhook."

    def handle(self, *args, **options):
        inst = getattr(settings, "GREEN_API_INSTANCE_ID", "").strip()
        tok = getattr(settings, "GREEN_API_TOKEN_INSTANCE", "").strip()
        host = getattr(settings, "GREEN_API_HOST", "https://api.green-api.com").strip().rstrip("/")
        if not inst or not tok:
            self.stderr.write("GREEN_API_INSTANCE_ID / GREEN_API_TOKEN_INSTANCE not configured.")
            return

        # Ensure Green API queues incoming messages for HTTP polling
        try:
            set_url = f"{host}/waInstance{inst}/setSettings/{tok}"
            payload = json.dumps({
                "webhookUrl": "",
                "incomingWebhook": "yes",
                "outgoingMessageWebhook": "no",
                "outgoingAPIMessageWebhook": "no",
            }).encode("utf-8")
            req = urllib.request.Request(
                set_url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "MindBridge/1.0"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=10).read()
            self.stdout.write(self.style.SUCCESS(f"Green API HTTP Poller active for instance {inst} (HTTPS port 443, no tunnel required)."))
        except Exception as exc:
            self.stderr.write(f"Warning configuring setSettings: {exc}")

        recv_url = f"{host}/waInstance{inst}/receiveNotification/{tok}?receiveTimeout=5"
        local_webhook = "http://127.0.0.1:8000/webhooks/green-api/"
        last_worker_sync = 0.0

        while True:
            now = time.time()
            if now - last_worker_sync >= 55.0:
                try:
                    call_command("run_workers", once=True)
                except Exception:
                    pass
                last_worker_sync = now

            try:
                req = urllib.request.Request(recv_url, headers={"User-Agent": "MindBridge/1.0"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    raw = resp.read().decode("utf-8").strip()
                if not raw or raw == "null":
                    continue
                notification = json.loads(raw)
                if not isinstance(notification, dict):
                    continue
                receipt_id = notification.get("receiptId")
                body = notification.get("body")
                if isinstance(body, dict):
                    try:
                        wh_req = urllib.request.Request(
                            local_webhook,
                            data=json.dumps(body).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                        with urllib.request.urlopen(wh_req, timeout=15) as wh_resp:
                            self.stdout.write(f"Forwarded event {body.get('typeWebhook')} (receipt {receipt_id}) -> HTTP {wh_resp.status}")
                    except Exception as wh_err:
                        self.stderr.write(f"Local webhook forward error: {wh_err}")
                if receipt_id is not None:
                    del_url = f"{host}/waInstance{inst}/deleteNotification/{tok}/{receipt_id}"
                    del_req = urllib.request.Request(del_url, headers={"User-Agent": "MindBridge/1.0"}, method="DELETE")
                    urllib.request.urlopen(del_req, timeout=8).read()
            except Exception as err:
                self.stderr.write(f"Poller transient error: {err}")
                time.sleep(2)
