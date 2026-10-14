"""Local walkthrough data, permission boundaries and realistic alarm regressions."""
import json
from html.parser import HTMLParser
from io import StringIO
from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .keyword_library import STARTER_KEYWORDS
from .keywords import matches_keyword
from .models import (AvailabilitySlot, CounsellorProfile, InboundMessage, Keyword, MoodEntry,
                     OutboundMessage, Participant, RiskAlert, Session, SessionRequest, WeeklyCheckIn)
from .risk import assess
from .response_policy import route
from .services import process_message
from .workflows import assign_counsellor


class HeaderParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.in_header = False; self.panel_in_header = False; self.title = []; self.in_title = False
    def handle_starttag(self, tag, attrs):
        if tag == 'header': self.in_header = True
        if tag == 'title': self.in_title = True
        if self.in_header and tag == 'section': self.panel_in_header = True
    def handle_endtag(self, tag):
        if tag == 'header': self.in_header = False
        if tag == 'title': self.in_title = False
    def handle_data(self, text):
        if self.in_title: self.title.append(text)


@override_settings(DEBUG=True, TURN_API_TOKEN='configured-but-must-not-send', SENTIMENT_ENABLED=False)
class PrepareWorkspaceTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('jadaw', password='existing-admin-test-password')
    def prepare(self):
        output = StringIO(); call_command('prepare_test_data', stdout=output); return output.getvalue()
    def test_ready_profiles_permissions_and_real_rule_scenarios(self):
        output = self.prepare()
        self.assertEqual(CounsellorProfile.objects.filter(is_simulated=True).count(), 3)
        self.assertEqual(Participant.objects.filter(is_simulated=True).count(), 6)
        self.assertEqual(AvailabilitySlot.objects.count(), 18)
        self.assertEqual(Keyword.objects.count(), len(STARTER_KEYWORDS))
        self.assertEqual(RiskAlert.objects.count(), 4)
        self.assertEqual(set(RiskAlert.objects.values_list('reason', flat=True)), {
            'Urgent keyword review', 'Consecutive low weekly moods', 'Sudden mood drop', 'Two missed weekly check-ins'})
        self.assertEqual(Session.objects.count(), 1)
        self.assertEqual(SessionRequest.objects.filter(status='pending').count(), 1)
        self.assertFalse(OutboundMessage.objects.exists())
        self.admin.refresh_from_db(); self.assertTrue(self.admin.check_password('existing-admin-test-password'))
        for profile in CounsellorProfile.objects.filter(is_simulated=True):
            self.assertFalse(profile.user.is_staff); self.assertFalse(profile.user.is_superuser)
            self.assertFalse(profile.notification_opt_in); self.assertEqual(profile.whatsapp_number, '')
            self.assertEqual(profile.user.participants.count(), 2)
            self.assertTrue(profile.user.get_full_name())
            password = next(line.split(': ', 1)[1] for line in output.splitlines()
                            if line.strip().startswith(profile.user.username+':'))
            self.assertIsNotNone(authenticate(username=profile.user.username, password=password))
        urgent = RiskAlert.objects.get(reason='Urgent keyword review')
        self.assertIn('might hurt myself', urgent.matched_terms)
        self.assertEqual(urgent.participant.display_name, 'Kelvin Otieno')
        self.assertFalse(Participant.objects.get(code='MB-1005').alerts.exists())
    def test_rerun_preserves_password_reviews_and_counts(self):
        self.prepare()
        user = get_user_model().objects.get(username='amina.otieno'); password = user.password
        alert = RiskAlert.objects.get(reason='Urgent keyword review'); alert.status='reviewed'; alert.save()
        models = (Participant, Keyword, MoodEntry, InboundMessage, RiskAlert, Session, SessionRequest, AvailabilitySlot, WeeklyCheckIn)
        counts = [m.objects.count() for m in models]
        self.prepare()
        self.assertEqual([m.objects.count() for m in models], counts)
        user.refresh_from_db(); self.assertEqual(user.password, password)
        alert.refresh_from_db(); self.assertEqual(alert.status, 'reviewed')
    @override_settings(DEBUG=False)
    def test_disabled_outside_development(self):
        with self.assertRaises(CommandError): self.prepare()
        self.assertFalse(CounsellorProfile.objects.exists()); self.assertFalse(Keyword.objects.exists())
    def test_existing_real_account_collision_is_not_modified(self):
        real = get_user_model().objects.create_user('amina.otieno', first_name='Real', password='kept-password')
        with self.assertRaises(CommandError): self.prepare()
        real.refresh_from_db(); self.assertEqual(real.first_name, 'Real'); self.assertTrue(real.check_password('kept-password'))
        self.assertFalse(Keyword.objects.exists())
    def test_live_assignment_excludes_fictional_counsellors(self):
        self.prepare()
        live = Participant.objects.create(code='LIVE', display_name='Unassigned')
        self.assertIsNone(assign_counsellor(live))
        real = get_user_model().objects.create_user('authorized.counsellor')
        CounsellorProfile.objects.create(user=real)
        self.assertEqual(assign_counsellor(live), real)
        simulated = Participant.objects.create(code='MB-CHAT-NEW', display_name='New participant', is_simulated=True)
        self.assertTrue(assign_counsellor(simulated).care_profile.is_simulated)
    def test_counsellor_sees_only_own_data_and_admin_header_is_clean(self):
        self.prepare()
        amina = get_user_model().objects.get(username='amina.otieno'); self.client.force_login(amina)
        self.assertContains(self.client.get(reverse('participants')), 'Kelvin Otieno')
        self.assertNotContains(self.client.get(reverse('participants')), 'Dennis Mwangi')
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 302)
        self.client.force_login(self.admin); response = self.client.get(reverse('admin_dashboard'))
        parser = HeaderParser(); parser.feed(response.content.decode())
        self.assertFalse(parser.panel_in_header)
        self.assertEqual(''.join(parser.title).strip(), 'Admin dashboard · Care workspace')
        self.assertContains(response, '<h3>Hybrid NLP and scheduled jobs</h3>', count=1, html=True)
        self.assertContains(response, '3 counsellors')
    def test_preview_naming_and_live_alert_reflection(self):
        self.prepare(); self.client.force_login(self.admin)
        for body in ('Hello', 'I agree', 'Kevin', '19', '3', 'I might hurt myself tonight.'):
            response = self.client.post(reverse('simulator_message'), json.dumps({'body': body}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
        person = Participant.objects.get(code=response.json()['code'])
        self.assertTrue(person.code.startswith('MB-CHAT-')); self.assertEqual(person.display_name, 'Kevin')
        self.assertTrue(person.counsellor.care_profile.is_simulated)
        self.assertTrue(person.alerts.filter(priority='high').exists())
        self.client.force_login(person.counsellor)
        self.assertContains(self.client.get(reverse('alerts')), 'might hurt myself')
        self.assertFalse(OutboundMessage.objects.exists())
    def test_full_booking_journey_reaches_named_counsellor_dashboard(self):
        self.prepare(); self.client.force_login(self.admin)
        for body in ('Hello', 'I agree', 'Kevin Kamau', '19', '3', 'School pressure has been difficult.', 'Counsellor'):
            response = self.client.post(reverse('simulator_message'), json.dumps({'body': body}), content_type='application/json')
            self.assertEqual(response.status_code, 200)
        person = Participant.objects.get(code=response.json()['code'])
        self.assertEqual(response.json()['state'], 'booking')
        self.assertTrue(person.session_requests.filter(status='pending').exists())
        counsellor_client = Client(); counsellor_client.force_login(person.counsellor)
        self.assertContains(counsellor_client.get(reverse('dashboard')), 'Kevin Kamau')
        response = self.client.post(reverse('simulator_message'), json.dumps({'body': '1'}), content_type='application/json')
        self.assertIn('confirmed', response.json()['reply'])
        session = person.sessions.get(status='scheduled')
        self.assertEqual(session.counsellor_id, person.counsellor_id)
        self.assertTrue(AvailabilitySlot.objects.filter(session=session).exists())
        self.assertFalse(person.session_requests.filter(status='pending').exists())
        self.assertContains(counsellor_client.get(reverse('sessions')), 'Kevin Kamau')
        self.assertFalse(OutboundMessage.objects.exists())

    def test_legacy_records_keep_identity_and_relationships(self):
        person = Participant.objects.create(code='DEMO-003', display_name='Sample participant C', is_simulated=True, counsellor=self.admin)
        session = Session.objects.create(participant=person, counsellor=self.admin, starts_at=timezone.now())
        self.prepare(); person.refresh_from_db(); session.refresh_from_db()
        self.assertEqual(person.code, 'MB-1003'); self.assertEqual(person.display_name, 'Samuel Ochieng')
        self.assertEqual(session.participant_id, person.pk); self.assertEqual(session.counsellor_id, person.counsellor_id)
        self.assertTrue(AvailabilitySlot.objects.filter(session=session).exists())


class ProposedKeywordTests(TestCase):
    def test_broad_library_is_idempotent_and_preserves_admin_choices(self):
        keyword = Keyword.objects.create(term='want to die', language='Customized', tier=2, is_active=False)
        call_command('add_keywords', stdout=StringIO()); call_command('add_keywords', stdout=StringIO())
        self.assertEqual(Keyword.objects.count(), len(STARTER_KEYWORDS))
        keyword.refresh_from_db(); self.assertEqual(keyword.tier, 2); self.assertFalse(keyword.is_active)
        self.assertEqual(keyword.language, 'Customized'); self.assertTrue(keyword.category)
        self.assertEqual(len({r[3] for r in STARTER_KEYWORDS}), 10)
    def test_context_and_negation_controls(self):
        for text, term in [('I am not being bullied', 'being bullied'), ('Si kwamba nataka kujiumiza', 'nataka kujiumiza'),
                           ('I no longer feel worthless', 'feel worthless'), ('Suicide prevention lesson', 'thinking about suicide')]:
            self.assertFalse(matches_keyword(text, term))
        self.assertTrue(matches_keyword('Si kwamba nataka kujiumiza, lakini nataka kujiumiza sasa.', 'nataka kujiumiza'))
        self.assertTrue(matches_keyword("I can't keep myself safe", 'cannot keep myself safe'))
    def test_urgent_library_and_reply_guard_agree(self):
        for term, language, tier, category in STARTER_KEYWORDS:
            if tier == 1:
                with self.subTest(term=term):
                    self.assertEqual(route(term), 'urgent')

    def test_supporting_concern_alone_does_not_raise_urgent_alarm(self):
        call_command('add_keywords', stdout=StringIO())
        person = Participant.objects.create(code='PHRASE', display_name='Fictional person', is_simulated=True)
        for text in ['Nabullyiwa shule.', 'Masomo yamenilemea.', 'I feel hopeless about school.', 'Naogopa kurudi home.']:
            self.assertIsNone(assess(person, text))
        self.assertEqual(assess(person, 'Nitafika shuleni kesho.'), None)
        self.assertEqual(assess(person, 'Siwezi keep myself safe.')[0], 'high')
