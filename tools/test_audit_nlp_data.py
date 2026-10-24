import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from audit_nlp_data import audit_data, fingerprints


class DataAuditTests(unittest.TestCase):
    def test_system_changes_do_not_hide_identical_training_conversations(self):
        row = {"messages": [{"role": "system", "content": "one"}, {"role": "user", "content": "Fictional message"}, {"role": "assistant", "content": "Fictional reply"}]}
        other = json.loads(json.dumps(row)); other["messages"][0]["content"] = "two"
        self.assertEqual(fingerprints([row]), fingerprints([other]))

    def test_directory_and_zip_detect_user_leakage_and_missing_lineage(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            def row(reply):
                return {"messages": [{"role": "user", "content": "Same fictional concern"}, {"role": "assistant", "content": reply}]}
            for name, reply in (("stage1_train.jsonl", "First reply"), ("stage1_validation.jsonl", "Different reply")):
                (folder / name).write_text(json.dumps(row(reply))+"\n")
            (folder / "two_stage_manifest.csv").write_text("record_id,group_id,split\n1,shared,train\n2,shared,validation\n")
            archive = folder / "data.zip"
            with zipfile.ZipFile(archive, "w") as output:
                for name in ("stage1_train.jsonl", "stage1_validation.jsonl", "two_stage_manifest.csv"):
                    output.write(folder / name, name)
            for path in (folder, archive):
                result = audit_data(path)
                overlap = result["heldout_overlap"]["stage1_validation.jsonl"]
                self.assertEqual(overlap["conversation_overlap_with_training"], 0)
                self.assertEqual(overlap["individual_user_text_overlap_with_training"], 1)
                self.assertEqual(result["manifest_groups_in_multiple_splits"], 1)
                self.assertFalse(result["jsonl_has_record_ids"])


if __name__ == "__main__":
    unittest.main()
