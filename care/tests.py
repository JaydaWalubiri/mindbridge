import base64
import hmac
import json
from hashlib import sha256
from datetime import date, datetime, time, timedelta
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from .models import AvailabilitySlot, CounsellorProfile, Keyword, InboundMessage, MoodEntry, OutboundMessage, Participant, RiskAlert, Session, SessionRequest, WeeklyCheckIn
from .services import process_message, deliver_due, queue_session_confirmation, run_weekly_checkins


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
        for idx, body in enumerate(["Hello", "I agree", "Demo Boy", "19", "3", "A little tired", "Talk to a counsellor"], 1):
            self.assertEqual(self.send(body, f"msg-{idx}").status_code, 200)
        person = Participant.objects.get(wa_id="254700000001")
        self.assertTrue(person.consented)
        self.assertEqual(person.moods.count(), 1)
        self.assertEqual(person.moods.first().score, 3)
        self.assertEqual(person.moods.first().note, "A little tired")
        self.assertEqual(SessionRequest.objects.filter(participant=person).count(), 1)
        self.send("2", "msg-7")
        self.assertEqual(SessionRequest.objects.filter(participant=person).count(), 1)
        self.assertEqual(InboundMessage.objects.count(), 7)
        self.send("Pause check-ins", "msg-8")
        person.refresh_from_db()
        self.assertFalse(person.consented)
        self.send("3", "msg-9")
        self.assertEqual(person.moods.count(), 1)

    def test_mood_rule_requires_three_distinct_consecutive_weeks(self):
        from django.utils import timezone
        for idx, body in enumerate(["I agree", "Demo Boy", "19"]):
            self.send(body, f"onboarding-{idx}")
        person = Participant.objects.get(wa_id="254700000001")
        for days in (14, 7):
            MoodEntry.objects.create(participant=person, score=2, recorded_at=timezone.now()-timedelta(days=days))
        self.send("2", "score")
        self.assertEqual(RiskAlert.objects.filter(reason="Consecutive low weekly moods").count(), 1)

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
        for idx, body in enumerate(["I agree", "Demo Boy", "19"]):
            self.send(body, f"optin-{idx}")
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
        self.assertEqual(self.client.get(reverse("whatsapp_preview")).status_code, 404)

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


@override_settings(DEBUG=True, TURN_API_TOKEN="", TURN_STAFF_TEMPLATE_NAME="")
class ProposalWorkflowTests(TestCase):
    def setUp(self):
        from django.utils import timezone
        self.now = timezone.now()
        users = get_user_model()
        self.admin = users.objects.create_user("review-admin", is_staff=True)
        self.c1 = users.objects.create_user("counsellor-one")
        self.c2 = users.objects.create_user("counsellor-two")
        CounsellorProfile.objects.create(user=self.c1)
        CounsellorProfile.objects.create(user=self.c2)
        self.client = Client(HTTP_HOST="localhost")
        self.counter = 0

    def person(self, code="TEST-1", age=19):
        person = Participant.objects.create(code=code, display_name="Pending")
        for body in ["I agree", "Demo Nick", str(age)]:
            self.say(person, body)
        person.refresh_from_db()
        return person

    def say(self, person, body):
        self.counter += 1
        msg, _ = process_message(person, body, f"{person.code}:{self.counter}")
        person.refresh_from_db()
        return msg.reply

    def test_round_robin_excludes_inactive_profiles_and_preserves_assignment(self):
        p1 = self.person("A")
        p2 = self.person("B")
        p3 = self.person("C")
        self.assertEqual([p1.counsellor_id,p2.counsellor_id,p3.counsellor_id], [self.c1.pk,self.c2.pk,self.c1.pk])
        self.say(p1,"Pause")
        self.say(p1,"I agree")
        self.assertEqual(p1.counsellor_id,self.c1.pk)
        self.c2.is_active=False
        self.c2.save()
        self.assertEqual(self.person("D").counsellor_id,self.c1.pk)

    def test_minor_agreement_before_assignment_and_mood_storage(self):
        person = self.person(age=16)
        self.assertFalse(person.onboarding_complete)
        self.assertIsNone(person.counsellor_id)
        self.say(person,"2")
        self.assertEqual(person.moods.count(),0)
        self.say(person,"I understand")
        self.assertTrue(person.onboarding_complete)
        self.assertIsNotNone(person.minor_assent_at)
        self.say(person,"3")
        self.assertEqual(person.moods.count(),1)

    def test_invalid_age_is_not_stored(self):
        person = self.person(age=12)
        self.assertIsNone(person.age)
        self.assertFalse(person.onboarding_complete)
        self.say(person,"25")
        self.assertIsNone(person.age)

    def test_slot_booking_and_duplicate_requests(self):
        person = self.person()
        slot = AvailabilitySlot.objects.create(counsellor=person.counsellor, starts_at=self.now+timedelta(days=2))
        self.assertIn("1.",self.say(person,"Counsellor"))
        self.say(person,"Counsellor")
        self.assertEqual(person.session_requests.filter(status="pending").count(),1)
        reply=self.say(person,"1")
        self.assertIn("confirmed",reply)
        self.assertEqual(person.sessions.count(),1)
        slot.refresh_from_db()
        self.assertIsNotNone(slot.session_id)
        self.assertFalse(person.session_requests.filter(status="pending").exists())
        self.assertEqual(person.moods.count(),0)  # Slot number must not become a mood.

    def test_stale_slot_cannot_double_book(self):
        from .workflows import book_appointment
        p1=self.person("A");p2=self.person("B")
        p2.counsellor=p1.counsellor;p2.save()
        slot=AvailabilitySlot.objects.create(counsellor=p1.counsellor,starts_at=self.now+timedelta(days=2))
        self.say(p1,"Counsellor");self.say(p2,"Counsellor")
        self.say(p1,"1")
        self.assertIn("no longer available",self.say(p2,"1"))
        self.assertEqual(Session.objects.count(),1)
        with self.assertRaises(ValueError):
            book_appointment(p2,p1.counsellor,slot.starts_at+timedelta(minutes=15))

    def test_requests_visible_only_to_assigned_counsellor(self):
        person=self.person();self.say(person,"Counsellor")
        self.client.force_login(self.c1)
        self.assertContains(self.client.get("/"),"Demo Nick")
        self.client.force_login(self.c2)
        self.assertNotContains(self.client.get("/"),"Demo Nick")

    def test_review_feedback_and_permission(self):
        person=self.person()
        alert=RiskAlert.objects.create(participant=person,reason="Test")
        url=reverse("review_alert",args=[alert.pk])
        self.client.force_login(self.c2)
        self.assertEqual(self.client.post(url,{"outcome":"false_positive"}).status_code,404)
        self.client.force_login(self.c1)
        self.client.post(url,{"outcome":"false_positive","review_note":"Reviewed with participant"})
        alert.refresh_from_db()
        self.assertEqual(alert.outcome,"false_positive")
        self.assertEqual(alert.review_note,"Reviewed with participant")

    def test_simulator_writes_demo_records_and_never_queues_delivery(self):
        self.client.force_login(self.admin)
        for body in ["I agree","Demo Chat","19","3","Counsellor"]:
            response=self.client.post(reverse("simulator_message"),json.dumps({"body":body}),content_type="application/json")
            self.assertEqual(response.status_code,200)
        person=Participant.objects.get(is_simulated=True)
        self.assertEqual(person.moods.count(),1)
        self.assertEqual(person.session_requests.count(),1)
        self.assertEqual(OutboundMessage.objects.count(),0)
        self.assertEqual(self.client.get(reverse("whatsapp_preview")).status_code,200)
        self.client.force_login(self.c1)
        self.assertEqual(self.client.post(reverse("simulator_message"),json.dumps({"body":"Hello"}),content_type="application/json").status_code,404)

    @override_settings(DEBUG=False)
    def test_simulator_disabled_outside_development(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("whatsapp_preview")).status_code,404)
        self.assertEqual(self.client.post(reverse("simulator_message"),json.dumps({"body":"Hello"}),content_type="application/json").status_code,404)

    def test_keyword_override_and_two_layer_agreement(self):
        from .model_ports import Classification
        person=self.person()
        Keyword.objects.create(term="distress example",language="en",tier=2)
        self.say(person,"distress example")
        self.assertEqual(person.alerts.count(),0)
        with patch("care.services.classify_note",return_value=Classification("negative",0.9)):
            self.say(person,"another message")
        self.assertEqual(person.alerts.get().trigger_source,"keyword, sentiment")
        Keyword.objects.create(term="urgent example",language="en",tier=1)
        self.say(person,"urgent example")
        self.assertTrue(person.alerts.filter(priority="high",trigger_source="Tier-1 keyword override").exists())

    def test_escalation_is_idempotent_and_visible_to_admin(self):
        from .workflows import run_escalations
        person=self.person()
        alert=RiskAlert.objects.create(participant=person,reason="Test")
        RiskAlert.objects.filter(pk=alert.pk).update(created_at=self.now-timedelta(hours=25))
        self.assertEqual(run_escalations(),1)
        self.assertEqual(run_escalations(),0)
        alert.refresh_from_db()
        self.assertIsNotNone(alert.escalated_at)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("admin_dashboard")),person.code)

    def test_retention_and_deletion_request(self):
        from .workflows import enforce_retention
        person=self.person()
        MoodEntry.objects.create(participant=person,score=3,recorded_at=self.now-timedelta(days=400))
        MoodEntry.objects.create(participant=person,score=4,recorded_at=self.now)
        enforce_retention(self.now)
        self.assertEqual(person.moods.count(),1)
        self.say(person,"Delete my data")
        self.assertFalse(person.consented)
        person.deletion_requested_at=self.now-timedelta(days=30)
        person.save()
        enforce_retention(self.now)
        self.assertFalse(Participant.objects.filter(pk=person.pk).exists())

    def test_all_review_pages_render(self):
        person=self.person()
        self.client.force_login(self.admin)
        for url in ["/","/alerts/","/participants/",f"/participants/{person.pk}/",f"/participants/{person.pk}/sessions/new/","/sessions/","/availability/","/workspace-admin/","/preview/whatsapp/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code,200)

    def test_availability_validation_and_staff_creation_for_counsellor(self):
        when=self.now+timedelta(days=3)
        data={"starts_at_0":when.date().isoformat(),"starts_at_1":"10:00","counsellor":self.c1.pk}
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("availability"),data).status_code,302)
        self.assertTrue(AvailabilitySlot.objects.filter(counsellor=self.c1).exists())
        self.assertContains(self.client.post(reverse("availability"),data),"overlaps")
        self.client.force_login(self.c2)
        data["starts_at_1"]="11:00"
        self.client.post(reverse("availability"),data)
        self.assertEqual(AvailabilitySlot.objects.filter(counsellor=self.c2).count(),1)

    def test_cannot_remove_another_counsellors_slot(self):
        slot=AvailabilitySlot.objects.create(counsellor=self.c1,starts_at=self.now+timedelta(days=3))
        self.client.force_login(self.c2)
        self.assertEqual(self.client.post(reverse("remove_availability",args=[slot.pk])).status_code,404)

    def test_session_cancellation_disables_slot_and_pending_confirmation(self):
        from .workflows import book_appointment
        person=self.person();person.wa_id="254700000001";person.save()
        slot=AvailabilitySlot.objects.create(counsellor=person.counsellor,starts_at=self.now+timedelta(days=3))
        session,queued=book_appointment(person,person.counsellor,slot.starts_at,slot.pk)
        self.assertIsNotNone(queued)
        self.client.force_login(self.c1)
        self.client.post(reverse("update_session",args=[session.pk]),{"status":"cancelled"})
        slot.refresh_from_db();queued.refresh_from_db();session.refresh_from_db()
        self.assertIsNone(slot.session_id)
        self.assertFalse(slot.is_active)
        self.assertEqual(queued.status,"cancelled")
        self.assertEqual(session.status,"cancelled")

    @override_settings(TURN_STAFF_TEMPLATE_NAME="staff_notice",TURN_TEMPLATE_NAMESPACE="approved_namespace")
    def test_staff_notice_requires_opt_in_and_delivery_rechecks_opt_in(self):
        from .workflows import create_alert
        person=self.person()
        profile=self.c1.care_profile
        profile.whatsapp_number="254700000010";profile.notification_opt_in=True;profile.save()
        alert=create_alert(person,"high","Test urgent","keyword")
        item=OutboundMessage.objects.get(dedupe_key=f"alert:{alert.pk}")
        self.assertEqual(item.payload["to"],profile.whatsapp_number)
        profile.notification_opt_in=False;profile.save()
        deliver_due()
        item.refresh_from_db()
        self.assertEqual(item.status,"cancelled")

    def test_urgent_free_text_still_checked_during_booking(self):
        person=self.person()
        AvailabilitySlot.objects.create(counsellor=person.counsellor,starts_at=self.now+timedelta(days=3))
        self.say(person,"Counsellor")
        Keyword.objects.create(term="urgent example",language="en",tier=1)
        self.say(person,"urgent example")
        self.assertTrue(person.alerts.filter(priority="high").exists())

    def test_no_auto_assignment_when_no_eligible_counsellor(self):
        CounsellorProfile.objects.update(accepts_assignments=False)
        person=self.person()
        self.assertIsNone(person.counsellor_id)
        self.say(person,"Counsellor")
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("admin_dashboard")),"Awaiting counsellor assignment")
