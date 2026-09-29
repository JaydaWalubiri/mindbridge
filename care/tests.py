import base64
import hmac
import json
from hashlib import sha256
from datetime import date, datetime, time, timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .models import InboundMessage, MoodEntry, OutboundMessage, Participant, RiskAlert, Session, SessionRequest, WeeklyCheckIn
from .services import deliver_due, queue_session_confirmation, run_weekly_checkins


@override_settings(TURN_WEBHOOK_SECRET="test-webhook-secret", TURN_API_TOKEN="")
class WebhookTests(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST="localhost")

    def send(self, body, msg_id):
        payload = json.dumps({"messages": [{"id": msg_id, "from": "254700000001",
                              "type": "text", "text": {"body": body}}]}).encode()
        signature = base64.b64encode(hmac.new(b"test-webhook-secret", payload, sha256).digest()).decode()
        return self.client.post("/webhooks/turn/", data=payload, content_type="application/json",
                                HTTP_X_TURN_HOOK_SIGNATURE=signature,
                                HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp")

    def test_rejects_unsigned_webhook(self):
        response = self.client.post("/webhooks/turn/", data=b"{}", content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Participant.objects.exists())

    def test_opt_in_mood_note_and_session_request(self):
        for idx, body in enumerate(["Hello", "I agree", "3", "A little tired", "Talk to a counsellor"], 1):
            self.assertEqual(self.send(body, f"msg-{idx}").status_code, 200)
        person = Participant.objects.get(wa_id="254700000001")
        self.assertTrue(person.consented)
        self.assertEqual(person.moods.count(), 1)
        self.assertEqual(person.moods.first().score, 3)
        self.assertEqual(person.moods.first().note, "A little tired")
        self.assertEqual(SessionRequest.objects.filter(participant=person).count(), 1)
        self.send("2", "msg-5")
        self.assertEqual(SessionRequest.objects.filter(participant=person).count(), 1)
        self.assertEqual(InboundMessage.objects.count(), 5)
        self.send("Pause check-ins", "msg-6")
        person.refresh_from_db()
        self.assertFalse(person.consented)
        self.send("3", "msg-7")
        self.assertEqual(person.moods.count(), 1)

    def test_mood_rule_creates_one_review_alert(self):
        self.send("I agree", "start")
        for n in range(3):
            if n:
                self.send("Check in again", f"mood-{n}")
            self.send("2", f"score-{n}")
        self.assertEqual(MoodEntry.objects.count(), 3)
        self.assertEqual(RiskAlert.objects.filter(reason="Mood pattern review").count(), 1)

    def test_interactive_consent_is_queued_once_and_no_network_in_webhook(self):
        payload = json.dumps({"messages": [{"id": "interactive-1", "from": "254700000001",
                              "type": "interactive", "interactive": {"button_reply": {
                                  "id": "consent_yes", "title": "I agree"}}}]}).encode()
        signature = base64.b64encode(hmac.new(b"test-webhook-secret", payload, sha256).digest()).decode()
        with patch("care.services.send_turn_payload") as sender:
            for _ in range(2):
                self.client.post("/webhooks/turn/", data=payload, content_type="application/json",
                                 HTTP_X_TURN_HOOK_SIGNATURE=signature,
                                 HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp")
            sender.assert_not_called()
        self.assertEqual(OutboundMessage.objects.count(), 1)
        self.assertTrue(Participant.objects.get(wa_id="254700000001").consented)

    @override_settings(TURN_API_TOKEN="fake-token")
    def test_delivery_retries_and_marks_accepted_reply(self):
        self.send("Hello", "initial")
        item = OutboundMessage.objects.get()
        self.assertEqual(item.payload["type"], "interactive")
        with patch("care.services.send_turn_payload", side_effect=OSError("offline")):
            self.assertEqual(deliver_due(), 0)
        item.refresh_from_db()
        self.assertEqual(item.attempts, 1)
        item.next_attempt_at = item.created_at
        item.save(update_fields=["next_attempt_at"])
        with patch("care.services.send_turn_payload", return_value="turn-accepted-id"):
            self.assertEqual(deliver_due(), 1)
        item.refresh_from_db()
        self.assertEqual(item.status, "sent")
        self.assertTrue(item.inbound.delivered)

    @override_settings(TURN_TEMPLATE_NAMESPACE="namespace", TURN_CHECKIN_TEMPLATE_NAME="weekly_checkin")
    def test_weekly_schedule_is_idempotent_and_flags_two_misses(self):
        self.send("I agree", "optin")
        person = Participant.objects.get(wa_id="254700000001")
        # The dates represent three weekly cycles since opt-in.
        monday = date.today() - timedelta(days=date.today().weekday())
        from django.utils import timezone
        start = timezone.make_aware(datetime.combine(monday - timedelta(days=14), time(12)))
        person.consented_at = start
        person.created_at = start
        person.save(update_fields=["consented_at", "created_at"])
        run_weekly_checkins(monday)
        run_weekly_checkins(monday)
        self.assertEqual(WeeklyCheckIn.objects.filter(participant=person).count(), 3)
        self.assertEqual(RiskAlert.objects.filter(reason="Two missed weekly check-ins").count(), 1)
        self.assertEqual(OutboundMessage.objects.filter(dedupe_key__startswith="weekly:").count(), 1)


class AccessTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(username="admin", password="test-pass-123", is_staff=True)
        self.counsellor = users.objects.create_user(username="care", password="test-pass-123")
        self.person = Participant.objects.create(code="P-1", display_name="Sample A", counsellor=self.admin)
        self.client = Client(HTTP_HOST="localhost")

    def test_counsellor_cannot_see_other_participant_or_admin_dashboard(self):
        self.client.force_login(self.counsellor)
        self.assertEqual(self.client.get(reverse("participant_detail", args=[self.person.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 302)

    def test_staff_can_review_alert_with_post_only(self):
        alert = RiskAlert.objects.create(participant=self.person, reason="Check-in review")
        self.client.force_login(self.admin)
        url = reverse("review_alert", args=[alert.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.status, "reviewed")
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("whatsapp_preview")).status_code, 200)

    @override_settings(TURN_TEMPLATE_NAMESPACE="namespace", TURN_SESSION_TEMPLATE_NAME="appointment")
    def test_session_confirmation_uses_approved_template_outside_recent_window(self):
        from django.utils import timezone
        self.person.wa_id = "254700000002"
        self.person.consented = True
        self.person.save(update_fields=["wa_id", "consented"])
        session = Session.objects.create(participant=self.person, counsellor=self.counsellor,
                                         starts_at=timezone.now() + timedelta(days=2))
        first = queue_session_confirmation(session)
        self.assertEqual(first.pk, queue_session_confirmation(session).pk)
        self.assertEqual(first.payload["type"], "template")
        self.assertEqual(len(first.payload["template"]["components"][0]["parameters"]), 1)
