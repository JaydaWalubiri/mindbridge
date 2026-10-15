"""Offline, hash-only audit of the two-stage ZIPs; never load model weights."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
import zipfile


class InputPackage:
    """Read a ZIP or its already-unpacked Kaggle input directory."""
    def __init__(self, path):
        self.path = Path(path)
        self.archive = None

    def __enter__(self):
        if self.path.is_file():
            self.archive = zipfile.ZipFile(self.path)
        return self

    def __exit__(self, *args):
        if self.archive:
            self.archive.close()

    def namelist(self):
        return self.archive.namelist() if self.archive else [p.name for p in self.path.iterdir() if p.is_file()]

    def read(self, name):
        return self.archive.read(name) if self.archive else (self.path / name).read_bytes()


def digest(value):
    value = unicodedata.normalize("NFKC", value).casefold()
    return hashlib.sha256(re.sub(r"\s+", " ", value).strip().encode()).hexdigest()


def fingerprints(rows, users_only=False):
    return {digest(json.dumps([(m["role"], m["content"]) for m in r["messages"]
                              if m["role"] == "user" or not users_only and m["role"] == "assistant"],
                             ensure_ascii=False)) for r in rows}


def audit_data(path):
    with InputPackage(path) as archive:
        rows = {n: [json.loads(line) for line in archive.read(n).decode("utf-8-sig").splitlines() if line.strip()]
                for n in archive.namelist() if n.endswith(".jsonl")}
        train = [r for n, values in rows.items() if n in ("stage1_train.jsonl", "stage2_style_train.jsonl") for r in values]
        train_turns = {digest(m["content"]) for r in train for m in r["messages"] if m["role"] == "user"}
        heldout = {}
        for name, values in rows.items():
            if "test" in name or "validation" in name:
                heldout[name] = {
                    "conversation_overlap_with_training": len(fingerprints(values) & fingerprints(train)),
                    "user_history_overlap_with_training": len(fingerprints(values, True) & fingerprints(train, True)),
                    "individual_user_text_overlap_with_training": len({digest(m["content"]) for r in values
                        for m in r["messages"] if m["role"] == "user"} & train_turns),
                }
        manifest_name = next((n for n in archive.namelist() if n.endswith("two_stage_manifest.csv")), None)
        groups = {}
        manifest = list(csv.DictReader(io.StringIO(archive.read(manifest_name).decode("utf-8-sig")))) if manifest_name else []
        for r in manifest:
            groups.setdefault(r["group_id"], set()).add(r["split"])
        return {
            "archive_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None,
            "jsonl_sha256": {n: hashlib.sha256(archive.read(n)).hexdigest() for n in rows},
            "files": {n: {"rows": len(v), "unique_conversations_without_system": len(fingerprints(v)),
                           "unique_user_histories": len(fingerprints(v, True))} for n, v in rows.items()},
            "heldout_overlap": heldout,
            "manifest_rows": len(manifest),
            "manifest_groups_in_multiple_splits": sum(len(s) > 1 for s in groups.values()),
            "jsonl_has_record_ids": all(all("record_id" in r for r in v) for v in rows.values()),
            "limitations": ["Exact normalized hashes cannot identify related translations or paraphrases.",
                            "Manifest grouping cannot be joined to JSONL messages without record IDs or content-hash mapping.",
                            "Held-out aliases overlap with each other by design; they are not independent test sets.",
                            "These conversation rows do not supply reviewed sentiment or risk labels."],
        }


def audit_results(path):
    with zipfile.ZipFile(path) as archive:
        def read(suffix):
            name = next(n for n in archive.namelist() if n.endswith(suffix))
            return archive.read(name).decode("utf-8-sig")
        reviews = list(csv.DictReader(io.StringIO(read("heldout_human_evaluation.csv"))))
        return {
            "archive_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "experiment": json.loads(read("experiment_metadata.json")),
            "adapter_task": json.loads(read("adapter_config.json")).get("task_type"),
            "saved_losses": {name: json.loads(read(name)) for name in
                             ("stage2_test_metrics.json", "broad_test_after_stage2_metrics.json", "stage2_validation_metrics.json")},
            "human_review_rows": len(reviews),
            "completed_review_fields": {k: sum(bool(r.get(k, "").strip()) for r in reviews)
                                        for k in ("language_match_score", "helpfulness_score", "safety_score", "notes")},
            "interpretation": "Conversation-model losses are not sentiment or hybrid-risk accuracy metrics. This archive predates the selected adapter revision.",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-zip", type=Path, required=True)
    parser.add_argument("--results-zip", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"data": audit_data(args.data_zip)}
    if args.results_zip:
        result["results"] = audit_results(args.results_zip)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print("Hash-only audit saved:", args.output)


if __name__ == "__main__":
    main()
