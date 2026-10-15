"""Check annotation/leakage/metric helpers with fictional rows; no model training."""
import ast
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support, cohen_kappa_score


def main():
    path = Path(__file__).resolve().parents[1] / "notebooks/MindBridge_DistilBERT_Training.ipynb"
    notebook = json.loads(path.read_text())
    context = dict(np=np, pd=pd, hashlib=__import__("hashlib"), LABELS=["negative", "neutral", "positive"],
                   LABEL_TO_ID={"negative": 0, "neutral": 1, "positive": 2},
                   LANGUAGES={"english", "kiswahili", "sheng", "code_switched"}, SEED=42, THRESHOLD=.85,
                   classification_report=classification_report, confusion_matrix=confusion_matrix,
                   precision_recall_fscore_support=precision_recall_fscore_support, cohen_kappa_score=cohen_kappa_score)
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code" and not "".join(cell["source"]).startswith("%pip"):
            tree = ast.parse("".join(cell["source"]))
            definitions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name != "tokenize"]
            exec(compile(ast.Module(body=definitions, type_ignores=[]), str(path), "exec"), context)
    rows = [dict(sample_id=f"{s}-{i}", group_id=f"{s}-{i}", text=f"{s} fictional {label}",
                 language="english", source="fictional pipeline test", source_license="test only",
                 split=s, rater_1=label, rater_2=label, adjudicator="")
            for s in ("train", "validation", "test") for i, label in enumerate(context["LABELS"])]
    raw = pd.DataFrame(rows)
    validate = context["validate_labels"]
    ready = validate(raw)
    for kind in ("group_leak", "text_leak", "disagreement", "invalid_label", "missing_licence", "empty", "duplicate_id"):
        bad = raw.copy()
        if kind == "group_leak": bad.loc[3, "group_id"] = bad.loc[0, "group_id"]
        elif kind == "text_leak": bad.loc[3, "text"] = bad.loc[0, "text"]
        elif kind == "disagreement": bad.loc[0, "rater_2"] = "neutral"
        elif kind == "invalid_label": bad.loc[0, "rater_1"] = "high risk"
        elif kind == "missing_licence": bad.loc[0, "source_license"] = ""
        elif kind == "empty": bad = bad.iloc[:0]
        else: bad.loc[1, "sample_id"] = bad.loc[0, "sample_id"]
        try:
            validate(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Guard failed: {kind}")
    probs = np.array([[.9, .05, .05], [.02, .96, .02], [.05, .05, .9]])
    assert context["threshold_metrics"]([0, 1, 2], probs, .85)["precision"] == 1
    assert context["threshold_metrics"]([0, 1, 2], probs, 1)["precision"] is None
    report = context["evaluation_report"](ready[ready.split.eq("test")].reset_index(drop=True), probs)
    assert report["sheng"]["status"] == "missing stratum"
    assert report["overall"]["classification"]["macro avg"]["f1-score"] == 1
    print("PASS: notebook syntax, seven annotation/leakage guards and metric helpers. Fictional checks only; no model trained or evaluated.")


if __name__ == "__main__":
    main()
