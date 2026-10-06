"""Load proposed starter phrases for testing, pending counsellor review."""
from django.core.management.base import BaseCommand
from django.db import transaction
from care.models import Keyword

STARTER_KEYWORDS = [
    ("want to kill myself", "English", 1),
    ("want to end my life", "English", 1),
    ("thinking about suicide", "English", 1),
    ("want to hurt myself", "English", 1),
    ("want to die", "English", 1),
    ("nataka kujiua", "Kiswahili", 1),
    ("nafikiria kujiua", "Kiswahili", 1),
    ("nataka kujidhuru", "Kiswahili", 1),
    ("nataka kufa", "Kiswahili", 1),
    ("sitaki kuishi", "Kiswahili", 1),
    ("feel hopeless", "English", 2),
    ("feel worthless", "English", 2),
    ("feel like a burden", "English", 2),
    ("feel trapped", "English", 2),
    ("feel completely alone", "English", 2),
    ("sina matumaini", "Kiswahili", 2),
    ("najiona sina thamani", "Kiswahili", 2),
    ("najiona mzigo", "Kiswahili", 2),
    ("najihisi mpweke", "Kiswahili", 2),
    ("sijui nifanye nini", "Kiswahili", 2),
    ("niko down sana", "Code-switched", 2),
    ("life imenishinda", "Code-switched", 2),
]


class Command(BaseCommand):
    help = "Add 22 starter risk phrases for testing without changing existing entries."

    @transaction.atomic
    def handle(self, *args, **options):
        created = 0
        for term, language, tier in STARTER_KEYWORDS:
            if Keyword.objects.filter(term__iexact=term).exists():
                continue
            Keyword.objects.create(term=term, language=language, tier=tier, is_active=True)
            created += 1
        self.stdout.write(self.style.SUCCESS(
            f"Added {created} keywords; kept {len(STARTER_KEYWORDS) - created} existing entries."
        ))
        self.stdout.write(
            "Starter list is for testing. Obtain counsellor review before live use. "
            "Matching does not yet understand negation or spelling variations."
        )
