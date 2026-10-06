import sys
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from .model_ports import Classification, _load_model, classify_note
from .models import Keyword, MoodEntry, Participant
from .services import process_message


@override_settings(SENTIMENT_ENABLED=True, SENTIMENT_MODEL="test/model", SENTIMENT_REVISION="test-revision",
                   SENTIMENT_RISK_ENABLED=False)
class SentimentAdapterTests(SimpleTestCase):
    def setUp(self):
        _load_model.cache_clear()
        self.tokenizer = MagicMock(return_value={"input_ids": "tokens"})
        self.model = MagicMock()
        self.model.config.id2label = {0: "NEGATIVE", 1: "POSITIVE"}
        self.scores = MagicMock()
        self.scores.argmax.return_value.item.return_value = 0
        self.scores.__getitem__.return_value.item.return_value = 0.92
        self.model.return_value.logits.__getitem__.return_value.softmax.return_value = self.scores
        self.torch = MagicMock()

    def tearDown(self):
        _load_model.cache_clear()

    def predict(self):
        with patch("care.model_ports._load_model", return_value=(self.tokenizer, self.model)), \
             patch.dict(sys.modules, {"torch": self.torch}):
            return classify_note("Fictional test message")

    def test_label_confidence_source_and_baseline_flag(self):
        result = self.predict()
        self.assertEqual(result, Classification("negative", 0.92, "test/model@test-revision", False))
        self.tokenizer.assert_called_once_with("Fictional test message", return_tensors="pt",
                                               truncation=True, max_length=512)

    @override_settings(SENTIMENT_RISK_ENABLED=True)
    def test_explicit_risk_opt_in(self):
        self.assertTrue(self.predict().risk_eligible)

    @override_settings(SENTIMENT_ENABLED=False)
    def test_disabled_does_not_load(self):
        with patch("care.model_ports._load_model") as loader:
            self.assertIsNone(classify_note("text"))
            loader.assert_not_called()

    def test_empty_input_does_not_load(self):
        with patch("care.model_ports._load_model") as loader:
            self.assertIsNone(classify_note("   "))
            loader.assert_not_called()

    def test_missing_model_returns_no_prediction(self):
        with patch("care.model_ports._load_model", return_value=None):
            self.assertIsNone(classify_note("text"))

    def test_invalid_scores_are_rejected(self):
        for score in (float("nan"), float("inf"), -0.1, 1.1):
            with self.subTest(score=score):
                self.scores.__getitem__.return_value.item.return_value = score
                self.assertIsNone(self.predict())

    def test_inference_failure_logs_no_participant_text(self):
        self.tokenizer.side_effect = RuntimeError("private test text")
        with self.assertLogs("care.model_ports", level="WARNING") as logs:
            self.assertIsNone(self.predict())
        self.assertNotIn("private test text", " ".join(logs.output))

    def test_loading_is_cached_and_offline_by_default(self):
        tokenizer_class = MagicMock()
        model_class = MagicMock()
        model_class.from_pretrained.return_value.config.id2label = {0: "NEGATIVE", 1: "POSITIVE"}
        fake = SimpleNamespace(AutoTokenizer=tokenizer_class, AutoModelForSequenceClassification=model_class)
        with patch.dict(sys.modules, {"transformers": fake}):
            first = _load_model("test/model", "rev")
            self.assertIs(first, _load_model("test/model", "rev"))
        tokenizer_class.from_pretrained.assert_called_once_with("test/model", revision="rev",
            local_files_only=True, trust_remote_code=False)
        model_class.from_pretrained.assert_called_once_with("test/model", revision="rev",
            local_files_only=True, trust_remote_code=False, use_safetensors=True)

    def test_unknown_label_mapping_is_not_guessed(self):
        fake = SimpleNamespace(AutoTokenizer=MagicMock(), AutoModelForSequenceClassification=MagicMock())
        fake.AutoModelForSequenceClassification.from_pretrained.return_value.config.id2label = {0: "LABEL_0"}
        with patch.dict(sys.modules, {"transformers": fake}), self.assertLogs("care.model_ports"):
            self.assertIsNone(_load_model("test/model", "rev"))

    def test_command_uses_only_fictional_smoke_text(self):
        output = StringIO()
        with patch("care.management.commands.check_sentiment.classify_note",
                   return_value=Classification("positive", 0.9)):
            call_command("check_sentiment", stdout=output)
        self.assertIn("test/model@test-revision", output.getvalue())
        self.assertIn("not clinical or multilingual evaluation", output.getvalue())


class SentimentStorageTests(TestCase):
    def setUp(self):
        self.person = Participant.objects.create(code="TEST-SENTIMENT", display_name="Fictional participant",
            consented=True, onboarding_complete=True, is_simulated=True, flow_state="note")
        self.mood = MoodEntry.objects.create(participant=self.person, score=3, recorded_at=timezone.now())
        Keyword.objects.create(term="feel hopeless", language="English", tier=2)

    def test_baseline_scores_are_saved_but_not_used_for_risk(self):
        prediction = Classification("negative", 0.94, "test/model@revision", False)
        with patch("care.services.classify_note", return_value=prediction):
            message, _ = process_message(self.person, "I feel hopeless", "baseline")
        self.mood.refresh_from_db()
        for item in (message, self.mood):
            self.assertEqual(item.sentiment_label, "negative")
            self.assertEqual(item.sentiment_score, 0.94)
            self.assertEqual(item.sentiment_source, "test/model@revision")
            self.assertFalse(item.sentiment_risk_eligible)
        self.assertFalse(self.person.alerts.exists())
        self.assertFalse(self.person.risk_evidence.filter(layer="sentiment").exists())

    def test_eligible_score_combines_with_keyword(self):
        with patch("care.services.classify_note", return_value=Classification("negative", 0.9, "test/model@rev", True)):
            process_message(self.person, "I feel hopeless", "eligible")
        self.assertEqual(self.person.alerts.get().trigger_source, "keyword, sentiment")

    def test_missing_prediction_does_not_block_urgent_keyword(self):
        Keyword.objects.create(term="nataka kujiua", language="Kiswahili", tier=1)
        with patch("care.services.classify_note", return_value=None):
            process_message(self.person, "nataka kujiua", "fallback")
        self.assertEqual(self.person.alerts.get().priority, "high")

    def test_missing_prediction_clears_old_mood_classification(self):
        self.mood.sentiment_label = "negative"
        self.mood.sentiment_score = 0.99
        self.mood.sentiment_source = "old/model"
        self.mood.save()
        with patch("care.services.classify_note", return_value=None):
            process_message(self.person, "new note", "no-prediction")
        self.mood.refresh_from_db()
        self.assertEqual(self.mood.sentiment_label, "")
        self.assertIsNone(self.mood.sentiment_score)
        self.assertEqual(self.mood.sentiment_source, "")
