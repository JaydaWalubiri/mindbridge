import base64
import hmac
import json
from hashlib import sha256
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .models import InboundMessage, MoodEntry, Participant, RiskAlert, SessionRequest


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
