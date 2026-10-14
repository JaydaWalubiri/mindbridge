"""Load proposed review phrases while preserving administrator choices."""
from django.core.management.base import BaseCommand
from django.db import transaction
from care.keyword_library import STARTER_KEYWORDS
from care.models import Keyword


class Command(BaseCommand):
    help = "Add a categorized English, Kiswahili and Sheng risk phrase library."

    @transaction.atomic
    def handle(self, *args, **options):
        created = categorized = 0
        for term, language, tier, category in STARTER_KEYWORDS:
            existing = Keyword.objects.filter(term__iexact=term).first()
            if existing:
                if not existing.category:
                    existing.category = category
                    existing.save(update_fields=["category"])
                    categorized += 1
                continue  # Preserve custom tier, language and activation choices.
            Keyword.objects.create(term=term, language=language, tier=tier,
                                   category=category, is_active=True)
            created += 1
        self.stdout.write(self.style.SUCCESS(
            f"Added {created} phrases; categorized {categorized} existing entries. "
            f"Library covers {len(STARTER_KEYWORDS)} proposed phrases."
        ))
        self.stdout.write("Tier 1: immediate review. Tier 2: supporting evidence, not an alarm by itself. "
                          "Obtain counsellor and native-language review before live use.")
