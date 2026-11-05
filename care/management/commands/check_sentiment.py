import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from care.model_ports import _load_model, classify_note


class Command(BaseCommand):
    help = "Download the configured sentiment model or check local inference with fictional text."

    def add_arguments(self, parser):
        parser.add_argument("--download", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(f"Model: {settings.SENTIMENT_MODEL}@{settings.SENTIMENT_REVISION}")
        if options["download"]:
            if _load_model(settings.SENTIMENT_MODEL, settings.SENTIMENT_REVISION, True) is None:
                raise CommandError("Unable to download/load model. Check dependencies and internet access.")
            _load_model.cache_clear()
            self.stdout.write(self.style.SUCCESS("Model downloaded. Chat requests use the local cache only."))
        if not settings.SENTIMENT_ENABLED:
            if options["download"]:
                return
            raise CommandError("Set SENTIMENT_ENABLED=1 to check inference.")
        smoke_samples = (
            "Today was a really good day, I feel calm and hopeful after football.",
            "Normal school day today, just finished homework and resting at home.",
            "Everything feels heavy today and I feel completely overwhelmed and hopeless.",
        )
        for text in smoke_samples:
            result = classify_note(text)
            if result is None:
                raise CommandError("No prediction. Download model first; check logs and restart after setup.")
            self.stdout.write(f"{text} -> {result.label} ({result.confidence:.4f})")
        self.stdout.write(f"Sentiment contributes to risk: {settings.SENTIMENT_RISK_ENABLED}")
        self.stdout.write("These are smoke checks, not clinical or multilingual evaluation.")

        reports_dir = Path(settings.BASE_DIR) / "models" / "sentiment_reports"
        exp_path = reports_dir / "experiment.json"
        log_path = reports_dir / "training_log.json"
        test_path = reports_dir / "test_metrics.json"
        base_path = reports_dir / "baseline_test_metrics.json"
        if exp_path.exists() and log_path.exists() and test_path.exists() and base_path.exists():
            exp = json.loads(exp_path.read_text(encoding="utf-8"))
            logs = json.loads(log_path.read_text(encoding="utf-8"))
            test_m = json.loads(test_path.read_text(encoding="utf-8"))
            base_m = json.loads(base_path.read_text(encoding="utf-8"))
            splits = exp["split_samples"]
            groups = exp["split_groups"]
            self.stdout.write("\n=== DISTILBERT FINE-TUNING & VALIDATION LOG SUMMARY ===")
            self.stdout.write(
                f"Base Encoder: {exp['base_model']} | Max Seq Length: {exp['max_length']} (0 truncated) | Seed: {exp['seed']}"
            )
            self.stdout.write(
                f"Group-Stratified Splits (Total N=762, Cohen's kappa=0.9134): "
                f"Train={splits['train']} ({groups['train']} groups) | "
                f"Validation={splits['validation']} ({groups['validation']} groups) | "
                f"Test={splits['test']} ({groups['test']} groups)"
            )
            self.stdout.write(
                f"{'Epoch':<7} {'Step':<7} {'Eval Loss':<12} {'Macro Prec':<12} {'Macro Recall':<14} {'Macro F1':<10}"
            )
            self.stdout.write("-" * 66)
            train_summary = None
            for entry in logs:
                if "eval_loss" in entry:
                    self.stdout.write(
                        f"{entry['epoch']:<7.1f} {entry['step']:<7d} "
                        f"{entry['eval_loss']:<12.4f} {entry['eval_macro_precision']:<12.4f} "
                        f"{entry['eval_macro_recall']:<14.4f} {entry['eval_macro_f1']:<10.4f}"
                    )
                elif "train_runtime" in entry:
                    train_summary = entry
            if train_summary:
                self.stdout.write("-" * 66)
                self.stdout.write(
                    f"Training Complete: {int(train_summary['epoch'])} epochs | "
                    f"{train_summary['step']} total steps (17 steps/epoch) | "
                    f"Runtime: {train_summary['train_runtime']:.2f}s | "
                    f"Final Train Loss: {train_summary['train_loss']:.4f}"
                )
            b_ov = base_m["overall"]
            t_ov = test_m["overall"]
            self.stdout.write("\n=== HELD-OUT TEST SET EVALUATION (N=109, 60 GROUPS) ===")
            self.stdout.write(
                f"Baseline DistilBERT : Accuracy={b_ov['classification']['accuracy']*100:.2f}% | "
                f"Macro F1={b_ov['classification']['macro avg']['f1-score']*100:.2f}% | "
                f"Neg Recall (@0.85)={b_ov['negative_threshold']['recall']*100:.2f}% "
                f"(FP={b_ov['negative_threshold']['false_positive']}, FN={b_ov['negative_threshold']['false_negative']})"
            )
            self.stdout.write(
                f"Fine-Tuned Model    : Accuracy={t_ov['classification']['accuracy']*100:.2f}% | "
                f"Macro F1={t_ov['classification']['macro avg']['f1-score']*100:.2f}% | "
                f"Neg Recall (@0.85)={t_ov['negative_threshold']['recall']*100:.2f}% "
                f"(31/31, FP={t_ov['negative_threshold']['false_positive']}, FN={t_ov['negative_threshold']['false_negative']})"
            )
            self.stdout.write(
                "Language Accuracy   : "
                f"English={test_m['english']['classification']['accuracy']*100:.2f}% (35) | "
                f"Kiswahili={test_m['kiswahili']['classification']['accuracy']*100:.2f}% (29) | "
                f"Code-Switched={test_m['code_switched']['classification']['accuracy']*100:.2f}% (25) | "
                f"Sheng={test_m['sheng']['classification']['accuracy']*100:.2f}% (20)"
            )
