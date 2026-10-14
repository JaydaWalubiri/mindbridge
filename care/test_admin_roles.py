from datetime import timedelta
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from .models import (AvailabilitySlot, CounsellorProfile, InboundMessage, MoodEntry,
                     Participant, RiskAlert, Session, SessionRequest, WeeklyCheckIn, RiskEvidence)


@override_settings(DEBUG=True)
class AdministratorRoleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser('system-admin', password='local-test-password')
        self.counsellor = User.objects.create_user('assigned-counsellor')
        CounsellorProfile.objects.create(user=self.counsellor)
        self.person = Participant.objects.create(code='ROLE-1', display_name='Fictional participant', counsellor=self.counsellor)
        self.alert = RiskAlert.objects.create(participant=self.person, reason='Follow-up', created_at=timezone.now()-timedelta(hours=25))
        RiskAlert.objects.filter(pk=self.alert.pk).update(created_at=timezone.now()-timedelta(hours=25))
        self.session = Session.objects.create(participant=self.person, counsellor=self.counsellor, starts_at=timezone.now()+timedelta(days=2))
        self.client.force_login(self.admin)

    def test_login_landing_and_navigation_are_administrative(self):
        self.assertRedirects(self.client.get('/'), reverse('admin_dashboard'))
        page = self.client.get(reverse('admin_dashboard'))
        self.assertContains(page, 'Counsellor availability')
        self.assertContains(page, self.person.code)
        self.assertContains(page, '0% review completion')
        self.assertNotContains(page, 'Counsellor portal')
        self.assertNotContains(page, 'My availability')
        self.assertNotContains(page, reverse('book_session', args=[self.person.pk]))

    def test_direct_case_urls_are_blocked(self):
        for name, args in [('alerts', []), ('participants', []), ('participant_detail', [self.person.pk]),
                           ('sessions', []), ('book_session', [self.person.pk])]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 403)

    def test_admin_cannot_submit_counsellor_actions(self):
        for name, args, data in [('review_alert', [self.alert.pk], {'outcome': 'concern_confirmed'}),
                                  ('update_session', [self.session.pk], {'status': 'completed'}),
                                  ('book_session', [self.person.pk], {})]:
            with self.subTest(name=name):
                self.assertEqual(self.client.post(reverse(name, args=args), data).status_code, 403)
        self.alert.refresh_from_db(); self.session.refresh_from_db()
        self.assertEqual(self.alert.status, 'open')
        self.assertEqual(self.session.status, 'scheduled')
        self.assertEqual(Session.objects.count(), 1)

    def test_superuser_cannot_edit_or_delete_case_records_in_django_admin(self):
        url = reverse('admin:care_riskalert_change', args=[self.alert.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {'status': 'reviewed'}).status_code, 403)
        self.assertEqual(self.client.post(reverse('admin:care_riskalert_delete', args=[self.alert.pk]), {'post': 'yes'}).status_code, 403)
        self.alert.refresh_from_db(); self.assertEqual(self.alert.status, 'open')
        for model in (MoodEntry, RiskAlert, Session, SessionRequest, InboundMessage, WeeklyCheckIn, RiskEvidence, AvailabilitySlot):
            item = admin.site._registry[model]
            request = type('Request', (), {'user': self.admin})()
            with self.subTest(model=model):
                self.assertTrue(item.has_view_permission(request))
                self.assertFalse(item.has_add_permission(request))
                self.assertFalse(item.has_change_permission(request))
                self.assertFalse(item.has_delete_permission(request))

    def test_admin_availability_requires_selected_counsellor(self):
        when = timezone.localdate()+timedelta(days=3)
        data = {'starts_at_0': when.isoformat(), 'starts_at_1': '10:00'}
        self.assertContains(self.client.post(reverse('availability'), data), 'This field is required')
        self.assertFalse(AvailabilitySlot.objects.exists())
        data['counsellor'] = self.admin.pk
        self.assertContains(self.client.post(reverse('availability'), data), 'Select a valid choice')
        data['counsellor'] = self.counsellor.pk
        self.assertEqual(self.client.post(reverse('availability'), data).status_code, 302)
        self.assertEqual(AvailabilitySlot.objects.get().counsellor, self.counsellor)

    def test_assigned_counsellor_can_still_review_and_manage_session(self):
        self.client.force_login(self.counsellor)
        self.assertEqual(self.client.post(reverse('review_alert', args=[self.alert.pk]), {'outcome': 'follow_up'}).status_code, 302)
        self.assertEqual(self.client.post(reverse('update_session', args=[self.session.pk]), {'status': 'completed'}).status_code, 302)
        self.alert.refresh_from_db(); self.session.refresh_from_db()
        self.assertEqual(self.alert.reviewed_by, self.counsellor)
        self.assertEqual(self.session.status, 'completed')

    def test_administrator_profile_is_never_assigned_cases(self):
        from .workflows import assign_counsellor
        CounsellorProfile.objects.create(user=self.admin)
        person = Participant.objects.create(code='ROLE-2', consented=True, onboarding_complete=True)
        assign_counsellor(person)
        person.refresh_from_db()
        self.assertEqual(person.counsellor, self.counsellor)
        self.assertContains(self.client.get(reverse("admin_dashboard")), "1 counsellors")
