"""Prepare isolated fictional profiles and realistic walkthrough scenarios."""
import secrets
from datetime import datetime, time, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from care.models import (AvailabilitySlot, CounsellorProfile, InboundMessage, MoodEntry,
                         Participant, Session, SessionRequest, WeeklyCheckIn)
from care.risk import assess, missed_checkin_signal
from care.services import process_message
from care.workflows import book_appointment, create_alert, overlapping

COUNSELLORS = [
    ("amina.otieno", "Amina", "Otieno"),
    ("brian.mwangi", "Brian", "Mwangi"),
    ("grace.wanjiru", "Grace", "Wanjiru"),
]
# Names, ages, notes and histories below are fictional; no real contacts are used.
PARTICIPANTS = [
    ("MB-1001", "Kelvin Otieno", 19, "Kibera", "en", 0, "urgent", [4, 3, 3, 2]),
    ("MB-1002", "Dennis Mwangi", 18, "Mathare", "sw", 1, "low", [3, 2, 2, 1]),
    ("MB-1003", "Samuel Ochieng", 20, "Mukuru", "sheng", 2, "drop", [4, 4, 5, 2]),
    ("MB-1004", "Peter Kamau", 17, "Kibera", "en", 0, "missed", [4]),
    ("MB-1005", "Hassan Ali", 21, "Mathare", "sw", 2, "positive", [4, 4, 5, 4]),
    ("MB-1006", "Daniel Mutua", 16, "Mukuru", "sheng", 1, "booking", [3, 3, 4, 3]),
]
NOTES = {
    "urgent": "School and home have felt difficult this week.",
    "low": "I have felt low for several weeks and would like someone to listen.",
    "drop": "Things changed suddenly this week and I am struggling to cope.",
    "missed": "The last completed check-in was three weeks ago.",
    "positive": "I enjoyed spending time with my friends this week.",
    "booking": "I would like a private counselling appointment about school pressure.",
}


class Command(BaseCommand):
    help = "Prepare 3 fictional counsellors, 6 participants, appointments and the keyword library."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Test setup requires DJANGO_DEBUG=1; it must not run in production.")
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            raise CommandError("Create your administrator first: python manage.py createsuperuser")
        call_command("add_keywords", stdout=self.stdout)
        users, credentials = [], []
        for username, first, last in COUNSELLORS:
            user, created = User.objects.get_or_create(username=username, defaults={
                "first_name": first, "last_name": last, "email": username+"@example.test",
                "is_staff": False, "is_superuser": False, "is_active": True,
            })
            if not created and not CounsellorProfile.objects.filter(user=user, is_simulated=True).exists():
                raise CommandError(f"{username} already belongs to a non-test account; it was not changed.")
            if created:
                password = secrets.token_urlsafe(12)
                user.set_password(password)
                user.save(update_fields=["password"])
                credentials.append((username, password))
            else:
                credentials.append((username, "unchanged — use the password already created"))
            CounsellorProfile.objects.get_or_create(user=user, defaults={
                "is_simulated": True, "accepts_assignments": True, "notification_opt_in": False,
            })
            users.append(user)
        now = timezone.now()
        today = timezone.localdate(now)
        week = today-timedelta(days=today.weekday())
        slots = {}
        for user in users:
            slots[user.pk] = []
            for days in (1, 2, 3):
                for hour in (10, 14):
                    starts = timezone.make_aware(datetime.combine(today+timedelta(days=days), time(hour)))
                    slot, _ = AvailabilitySlot.objects.get_or_create(counsellor=user, starts_at=starts)
                    slots[user.pk].append(slot)
        for index, (code, name, age, area, language, owner_index, scenario, scores) in enumerate(PARTICIPANTS, 1):
            person = Participant.objects.filter(code=code).first()
            migrated = False
            if not person and index <= 3:
                person = Participant.objects.filter(code=f"DEMO-{index:03}", is_simulated=True).first()
                if person:
                    person.code = code
                    migrated = True
            created = person is None
            if person and not person.is_simulated:
                raise CommandError(f"{code} belongs to a real participant; no real records were changed.")
            if created:
                person = Participant(code=code)
            if created or migrated:
                person.display_name, person.age, person.area = name, age, area
                person.preferred_language = language
                person.counsellor = users[owner_index]
                person.is_simulated = True
                person.onboarding_complete = person.consented = True
                person.consented_at = now-timedelta(days=28)
                person.minor_assent_at = person.consented_at if age < 18 else None
                person.flow_state = "menu"
                person.save()
                days_ago = (21,) if scenario == "missed" else (21, 14, 7, 0)
                for offset, score in zip(days_ago, scores):
                    MoodEntry.objects.create(participant=person, score=score,
                        recorded_at=now-timedelta(days=offset), note=NOTES[scenario])
                if migrated:
                    # Convert only the old placeholder alert, preserving its review status.
                    person.alerts.filter(trigger_source="Sample data").update(
                        reason={"urgent": "Urgent keyword review", "low": "Consecutive low weekly moods",
                                "drop": "Sudden mood drop"}[scenario],
                        priority="medium" if scenario == "low" else "high",
                        trigger_source="Tier-1 keyword override" if scenario == "urgent" else "mood rule")
                if scenario == "urgent":
                    assess(person, "I might hurt myself tonight.")
                    process_message(person, "I might hurt myself tonight.", f"fixture:{code}:urgent:v1")
                elif scenario in ("low", "drop"):
                    signal = assess(person)
                    if signal:
                        create_alert(person, *signal)
                elif scenario == "missed":
                    for offset in (14, 7, 0):
                        WeeklyCheckIn.objects.get_or_create(participant=person, week_start=week-timedelta(days=offset),
                            defaults={"status": "missed" if offset else "pending"})
                    signal = missed_checkin_signal(person, week)
                    if signal:
                        create_alert(person, *signal)
                elif scenario == "positive":
                    process_message(person, "I feel happy and supported today.", f"fixture:{code}:positive:v1")
                elif scenario == "booking":
                    SessionRequest.objects.get_or_create(participant=person, status="pending")
            if scenario == "drop" and migrated:
                legacy_session = person.sessions.filter(status="scheduled", availability_slot__isnull=True).first()
                if legacy_session:
                    User.objects.select_for_update().get(pk=person.counsellor_id)
                    slot = next((s for s in slots.get(person.counsellor_id, [])
                                 if s.is_active and not s.session_id
                                 and not overlapping(person.counsellor, s.starts_at, legacy_session.pk)), None)
                    if slot:
                        legacy_session.counsellor = person.counsellor
                        legacy_session.starts_at = slot.starts_at
                        legacy_session.save(update_fields=["counsellor", "starts_at"])
                        slot.session = legacy_session
                        slot.save(update_fields=["session"])
            if scenario == "drop" and not person.sessions.filter(status="scheduled", starts_at__gt=now).exists():
                slot = next((s for s in slots.get(person.counsellor_id, []) if s.is_active and not s.session_id), None)
                if slot:
                    book_appointment(person, person.counsellor, slot.starts_at, slot.pk)
        # Upgrade only old simulator identifiers; keep nicknames entered by the user.
        for person in Participant.objects.filter(is_simulated=True, code__startswith="DEMO-CHAT-"):
            new_code = person.code.replace("DEMO-CHAT-", "MB-CHAT-", 1)
            if not Participant.objects.filter(code=new_code).exists():
                person.code = new_code
                if person.display_name == "Demo participant":
                    person.display_name = "New participant"
                person.save(update_fields=["code", "display_name"])
        self.stdout.write(self.style.SUCCESS("Testing workspace prepared: 3 fictional counsellors and 6 named participants."))
        self.stdout.write("Counsellor sign-ins (save newly generated passwords; reruns do not reset them):")
        for username, password in credentials:
            self.stdout.write(f"  {username}: {password}")
        self.stdout.write("Administrator: use your existing superuser. No administrator password was changed.")
        self.stdout.write("Appointment slots: tomorrow and the next two days, at 10:00 and 14:00 EAT.")
        self.stdout.write("Profiles are fictional, marked as test data, and cannot receive live assignments or send WhatsApp messages.")
