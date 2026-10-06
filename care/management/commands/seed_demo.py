from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from care.models import CounsellorProfile, MoodEntry, Participant, RiskAlert, Session


class Command(BaseCommand):
    help = "Create clearly fictional sample dashboard records assigned to the first superuser."

    def handle(self, *args, **options):
        owner = get_user_model().objects.filter(is_superuser=True).order_by("pk").first()
        if not owner:
            raise CommandError("Create a superuser first: python manage.py createsuperuser")
        CounsellorProfile.objects.get_or_create(user=owner)
        now = timezone.now()
        samples = [
            ("DEMO-001", "Sample participant A", "Kibera", [4, 3, 3, 2], "Follow-up requested after check-in", "high"),
            ("DEMO-002", "Sample participant B", "Mathare", [3, 4, 3, 4], "Weekly check-in missed", "medium"),
            ("DEMO-003", "Sample participant C", "Mukuru", [4, 4, 3, 3], "Mood trend changed", "medium"),
        ]
        for code, name, area, scores, reason, priority in samples:
            person, _ = Participant.objects.get_or_create(code=code, defaults={
                "display_name": name, "area": area, "counsellor": owner, "is_simulated": True, "age": 19, "onboarding_complete": True,
            })
            if not person.moods.exists():
                for days_ago, score in zip((21, 14, 7, 0), scores):
                    MoodEntry.objects.create(participant=person, recorded_at=now - timedelta(days=days_ago), score=score)
            RiskAlert.objects.get_or_create(participant=person, reason=reason, defaults={
                "priority": priority, "trigger_source": "Sample data",
            })
        person = Participant.objects.get(code="DEMO-003")
        if not person.sessions.exists():
            Session.objects.create(participant=person, counsellor=owner, starts_at=now + timedelta(days=2))
        self.stdout.write(self.style.SUCCESS("Created fictional sample dashboard data."))
