"""Regression checks with fictional text and controlled dates, not model evaluation."""
from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from .keywords import matches_keyword
from .model_ports import Classification
from .models import InboundMessage, Keyword, MoodEntry, Participant, RiskEvidence
from .risk import assess
from .services import process_message, run_weekly_checkins


class KeywordMatchingTests(SimpleTestCase):
    def test_case_spacing_and_unicode(self):
        for text in ("I WANT TO DIE", "I want   to\ndie", "I want-to-die", "Ｉ want to die"):
            with self.subTest(text=text):
                self.assertTrue(matches_keyword(text, "want to die"))

    def test_controlled_variants(self):
        for text in ("I wanna die", "I want 2 die"):
            self.assertTrue(matches_keyword(text, "want to die"))
        self.assertTrue(matches_keyword("I am feeling hopeless", "feel hopeless"))

    def test_direct_negation(self):
        for text in ("I don't want to die", "I don’t want to die", "I do not want to die",
                     "I dont want to die", "I no longer want to die", "I never want to die",
                     "I don't really want to die"):
            with self.subTest(text=text):
                self.assertFalse(matches_keyword(text, "want to die"))
        self.assertFalse(matches_keyword("I am not feeling hopeless", "feel hopeless"))

    def test_ambivalence_is_not_suppressed(self):
        for text in ("I am not sure if I want to die", "I not only want to die",
                     "I don't want to die, but sometimes I want to die",
                     "I don't feel safe. I want to die"):
            with self.subTest(text=text):
                self.assertTrue(matches_keyword(text, "want to die"))

    def test_kiswahili_and_code_switching(self):
        self.assertTrue(matches_keyword("Leo NATaka kujiua!", "nataka kujiua"))
        self.assertFalse(matches_keyword("sitaki kujiua", "nataka kujiua"))
        self.assertTrue(matches_keyword("Leo niko down sana", "niko down sana"))

    def test_boundaries_empty_and_no_fuzzy_urgent_guess(self):
        self.assertFalse(matches_keyword("I want to diet", "want to die"))
        self.assertFalse(matches_keyword("anything", "  "))
        self.assertFalse(matches_keyword("I want to dye", "want to die"))

    def test_custom_phrases_remain_literal(self):
        self.assertTrue(matches_keyword("I don't want to live", "don't want to live"))
        self.assertTrue(matches_keyword("sitaki kuishi", "sitaki kuishi"))


@override_settings(RISK_NEGATIVE_THRESHOLD=0.85, TURN_API_TOKEN="")
class RiskRuleTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.person = Participant.objects.create(
            code="TEST-RISK", display_name="Fictional participant", consented=True,
            onboarding_complete=True, is_simulated=True, flow_state="menu",
        )

    def mood(self, days, score):
        return MoodEntry.objects.create(participant=self.person, score=score,
                                       recorded_at=self.now-timedelta(days=days))

    def test_three_consecutive_low_weeks(self):
        for days in (14, 7, 0):
            self.mood(days, 2)
        self.assertEqual(assess(self.person)[1], "Consecutive low weekly moods")

    def test_three_same_day_scores_are_not_three_weeks(self):
        for _ in range(3):
            self.mood(0, 2)
        self.assertIsNone(assess(self.person))

    def test_skipped_week_does_not_count(self):
        for days in (21, 7, 0):
            self.mood(days, 2)
        self.assertIsNone(assess(self.person))

    def test_latest_score_in_week_controls_low_rule(self):
        for days in (14, 7, 1):
            self.mood(days, 2)
        self.mood(0, 4)
        self.assertIsNone(assess(self.person))

    def test_stale_low_history_does_not_alert(self):
        for days in (24, 17, 10):
            self.mood(days, 2)
        self.assertIsNone(assess(self.person))

    def test_drop_of_three_is_high_priority(self):
        self.mood(1, 5)
        self.mood(0, 2)
        self.assertEqual(assess(self.person), ("high", "Sudden mood drop", "mood rule"))

    def test_drop_of_two_does_not_alert(self):
        self.mood(1, 4)
        self.mood(0, 2)
        self.assertIsNone(assess(self.person))

    def test_tier_one_works_without_classifier_and_deduplicates(self):
        Keyword.objects.create(term="nataka kujiua", language="Kiswahili", tier=1)
        process_message(self.person, "nataka kujiua", "risk-1")
        process_message(self.person, "nataka kujiua", "risk-2")
        self.assertEqual(self.person.alerts.count(), 1)
        self.assertEqual(self.person.alerts.get().trigger_source, "Tier-1 keyword override")

    def test_negated_phrase_does_not_create_keyword_evidence(self):
        Keyword.objects.create(term="want to die", language="English", tier=1)
        process_message(self.person, "I don't want to die", "negated-1")
        self.assertFalse(self.person.alerts.exists())
        self.assertFalse(self.person.risk_evidence.exists())

    def test_disabled_keyword_is_ignored(self):
        Keyword.objects.create(term="nataka kujiua", language="Kiswahili", tier=1, is_active=False)
        self.assertIsNone(assess(self.person, "nataka kujiua"))

    def test_multiple_keywords_are_one_layer(self):
        for term in ("feel hopeless", "feel worthless"):
            Keyword.objects.create(term=term, language="English", tier=2)
        self.assertIsNone(assess(self.person, "I feel hopeless and feel worthless"))
        self.assertEqual(set(self.person.risk_evidence.values_list("layer", flat=True)), {"keyword"})

    def test_sentiment_threshold_and_agreement(self):
        Keyword.objects.create(term="feel hopeless", language="English", tier=2)
        self.assertIsNone(assess(self.person, "I feel hopeless", Classification("negative", 0.849)))
        self.assertEqual(assess(self.person, "another concern", Classification("negative", 0.85)),
                         ("medium", "Combined risk signals", "keyword, sentiment"))

    def test_sentiment_alone_and_positive_are_not_combined_alerts(self):
        self.assertIsNone(assess(self.person, "text", Classification("negative", 0.95)))
        self.assertIsNone(assess(self.person, "text", Classification("positive", 0.99)))

    def test_expired_evidence_does_not_combine(self):
        RiskEvidence.objects.create(participant=self.person, layer="keyword", reason="old",
                                    recorded_at=self.now-timedelta(days=8))
        self.assertIsNone(assess(self.person, "text", Classification("negative", 0.9)))

    def test_neutral_message_does_not_retrigger_old_combination(self):
        for layer in ("keyword", "sentiment"):
            RiskEvidence.objects.create(participant=self.person, layer=layer, reason="previous")
        self.assertIsNone(assess(self.person, "Thank you"))


@override_settings(TURN_API_TOKEN="", TURN_TEMPLATE_NAMESPACE="")
class MissedCheckInTests(TestCase):
    def setUp(self):
        self.monday = timezone.localdate()
        self.monday -= timedelta(days=self.monday.weekday())
        self.start = timezone.make_aware(datetime.combine(self.monday-timedelta(days=14), time(12)))
        self.person = Participant.objects.create(code="TEST-MISSED", display_name="Fictional participant",
            wa_id="254700000099", consented=True, onboarding_complete=True, consented_at=self.start)

    def test_two_missed_weeks_flag_once(self):
        run_weekly_checkins(self.monday)
        run_weekly_checkins(self.monday)
        self.assertEqual(self.person.alerts.filter(reason="Two missed weekly check-ins").count(), 1)

    def test_one_missed_week_does_not_flag(self):
        self.person.consented_at = self.start+timedelta(days=7)
        self.person.save()
        run_weekly_checkins(self.monday)
        self.assertFalse(self.person.alerts.exists())

    def test_other_contact_prevents_disengagement_flag(self):
        message = InboundMessage.objects.create(participant=self.person, external_id="contact", body="Hello")
        InboundMessage.objects.filter(pk=message.pk).update(received_at=self.start+timedelta(days=1))
        run_weekly_checkins(self.monday)
        self.assertFalse(self.person.alerts.exists())

    def test_completed_week_breaks_missed_streak(self):
        MoodEntry.objects.create(participant=self.person, score=3, recorded_at=self.start+timedelta(days=8))
        run_weekly_checkins(self.monday)
        self.assertFalse(self.person.alerts.exists())

    def test_paused_participant_is_excluded(self):
        self.person.consented = False
        self.person.save()
        run_weekly_checkins(self.monday)
        self.assertFalse(self.person.weekly_checkins.exists())
