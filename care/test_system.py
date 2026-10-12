"""Fictional whole-system checks; provider calls and classifier weights are isolated."""
import base64
from datetime import timedelta
from hashlib import sha256
import hmac
from io import StringIO
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .model_ports import Classification, ReplyText
from .models import (AvailabilitySlot, CounsellorProfile, InboundMessage, Keyword,
                     OutboundMessage, Participant, RiskEvidence, WorkerStatus)
from .services import process_message, deliver_due
from .risk import assess


@override_settings(TURN_WEBHOOK_SECRET="fictional-secret", TURN_API_TOKEN="fictional-token",
                   TURN_STAFF_TEMPLATE_NAME="staff", TURN_TEMPLATE_NAMESPACE="fictional",
                   SENTIMENT_RISK_ENABLED=True)
class WholeJourneyTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("fictional-counsellor")
        CounsellorProfile.objects.create(user=self.user, notification_opt_in=True,
                                         whatsapp_number="254700000002")
        self.slot = AvailabilitySlot.objects.create(counsellor=self.user,
            starts_at=timezone.now()+timedelta(days=2))
        Keyword.objects.create(term="feel hopeless", language="English", tier=2)
        self.counter = 0

    def post(self, body, external_id=None):
        self.counter += 1
        payload = json.dumps({"messages": [{"id": external_id or f"whole-{self.counter}",
            "from": "254700000001", "type": "text", "text": {"body": body}}]}).encode()
        signature = base64.b64encode(hmac.new(b"fictional-secret",payload,sha256).digest()).decode()
        return self.client.post("/webhooks/turn/", payload, content_type="application/json",
            HTTP_X_TURN_HOOK_SIGNATURE=signature, HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp")

    def onboard(self):
        for value in ("I agree", "Fictional Nick", "19", "3"):
            self.assertEqual(self.post(value).status_code,200)
        return Participant.objects.get(wa_id="254700000001")

    def test_webhook_hybrid_reply_booking_dashboard_and_delivery(self):
        person = self.onboard()
        self.assertEqual(person.counsellor,self.user)
        with patch("care.services.classify_note",return_value=Classification("negative",.91,"fictional-sentiment@1",True)), \
             patch("care.services.generate_response",return_value=ReplyText("What would you like help with first?","fictional-reply@1")):
            self.post("I feel hopeless about finishing school", "unique-note")
            self.post("I feel hopeless about finishing school", "unique-note")
        self.assertEqual(person.alerts.get().trigger_source,"keyword, sentiment")
        self.assertEqual(person.moods.get().sentiment_source,"fictional-sentiment@1")
        self.assertEqual(InboundMessage.objects.get(external_id="unique-note").reply_source,"fictional-reply@1")
        self.assertEqual(InboundMessage.objects.filter(external_id="unique-note").count(),1)
        self.post("Counsellor")
        self.post("1")
        self.assertEqual(person.sessions.count(),1)
        self.client.force_login(self.user)
        profile=self.client.get(reverse("participant_detail",args=[person.pk]))
        self.assertContains(profile,"fictional-reply@1")
        self.assertContains(profile,"fictional-sentiment@1")
        self.assertEqual(self.client.get(reverse("sessions")).status_code,200)
        with patch("care.services.send_turn_payload",return_value="fictional-provider-id"):
            self.assertGreater(deliver_due(),0)
        self.assertFalse(OutboundMessage.objects.filter(status="pending").exists())
        self.assertTrue(InboundMessage.objects.get(external_id="unique-note").delivered)

    def test_active_urgent_alert_does_not_block_counsellor_booking(self):
        person=self.onboard()
        with patch("care.services.generate_response") as generator, patch("care.services.classify_note") as classifier:
            self.post("I intend to take my own life today")
            self.post("Counsellor")
            reply=InboundMessage.objects.order_by("-pk").first().reply
            self.assertIn("999",reply)
            self.assertIn("1.",reply)
            self.assertEqual(person.session_requests.filter(status="pending").count(),1)
            self.post("1")
            self.assertIn("confirmed",InboundMessage.objects.order_by("-pk").first().reply)
            self.assertEqual(person.sessions.count(),1)
            generator.assert_not_called()
            classifier.assert_not_called()
        self.assertEqual(person.alerts.filter(status="open").count(),1)

    def test_malformed_nested_provider_message_is_ignored(self):
        for kind,value in (("text",[]),("interactive","invalid")):
            payload=json.dumps({"messages":[{"id":"bad","from":"254700000001","type":kind,kind:value}]}).encode()
            signature=base64.b64encode(hmac.new(b"fictional-secret",payload,sha256).digest()).decode()
            response=self.client.post("/webhooks/turn/",payload,content_type="application/json",
                HTTP_X_TURN_HOOK_SIGNATURE=signature,HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp")
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()["received"],0)


class OperationsTests(TestCase):
    def test_worker_jobs_record_success_and_redacted_failure(self):
        actions=(("delivery",60,lambda: 0),("checkins",86400,lambda: (_ for _ in ()).throw(ValueError("PRIVATE SECRET"))))
        output=StringIO()
        with patch("care.management.commands.run_workers.TASKS",actions):
            with self.assertRaises(CommandError):
                call_command("run_workers",once=True,stdout=output,stderr=output)
        self.assertIsNotNone(WorkerStatus.objects.get(task="delivery").last_success_at)
        self.assertEqual(WorkerStatus.objects.get(task="checkins").last_error_type,"ValueError")
        self.assertNotIn("PRIVATE",output.getvalue())

    def test_readiness_does_not_make_network_calls(self):
        output=StringIO()
        with patch("care.services.send_turn_payload") as sender, patch("care.model_ports.build_opener") as opener:
            call_command("check_system",stdout=output)
            sender.assert_not_called();opener.assert_not_called()
        self.assertIn("NEEDS SETUP",output.getvalue())
        self.assertIn("do not prove Turn delivery",output.getvalue())

    @override_settings(SENTIMENT_RISK_ENABLED=False)
    def test_disabled_sentiment_cannot_reuse_old_risk_evidence(self):
        person=Participant.objects.create(code="OLD-EVIDENCE",display_name="Fictional")
        RiskEvidence.objects.create(participant=person,layer="sentiment",reason="old experiment")
        Keyword.objects.create(term="feel hopeless",language="English",tier=2)
        self.assertIsNone(assess(person,"I feel hopeless about school"))
