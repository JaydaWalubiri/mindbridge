# NLP audit and evaluation — 14 October 2026

## Finding

The prototype has working keyword/mood safeguards and conversation-service integration, but the complete three-layer NLP system has not been validated on independent labelled project data. Keep `SENTIMENT_RISK_ENABLED=0`. Application regression tests are not model-accuracy results.

| Component | Evidence | Remaining work |
| --- | --- | --- |
| Sentiment | Default is `distilbert/distilbert-base-uncased-finetuned-sst-2-english@714eb0fa89d2f80546fda750413ed43d93601a13`. The [official card](https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english) identifies an English SST-2 classifier, not a project-trained distress classifier. | Complete reviewed labels, source permissions and grouping; train/evaluate the separate classifier. |
| Conversation model | Selected adapter remains `Jayda13/mindbridge-uliza-clean-connection-20261007t073357z@785f05e6bec41f716e1226edd8e777b288b43cc6`; base revision `267ba2668e4119bf48e1cca544475293128775a9`. | Independent language, factuality, helpfulness and safety review; latency/completion measurement on the chosen host. |
| Earlier shared results ZIP | CAUSAL_LM LoRA, recovered Stage 2 step 362/362 from `f1af3aad969103f7f4af3225a5aa366b7517c906`; Stage 1 recorded 995 steps. Test losses 1.22959 (36 style examples) and 1.54757 (1,054 broad examples). | Those are whole-conversation token losses, not sentiment F1 or hybrid-alert accuracy. This ZIP predates the selected connection adapter. |
| Human reply review | 76 rows; zero completed language-match, helpfulness or safety scores. | Complete independent review; do not interpret the blank sheet as a passed evaluation. |
| Sheng repair | October 13 experimental adapter explicitly rejected for factuality/latency. Narrow scripted context routes have regression tests. | Do not present scripted replies as improved raw-model performance. |
| Hybrid engine | Mood/keyword exceptions and evidence aggregation tested with controlled examples. | Evaluate actual alerts against independently reviewed longitudinal risk scenarios. |

## Dataset integrity

The original data ZIP SHA256 is `392bb985e1fe1b859b0d09adf78e1321f272c535ad833a0233394dcf24df71a4`. The reproducible hash-only report is [nlp_data_audit.json](nlp_data_audit.json).

- Stage 1: 7,953 train, 1,051 validation and 1,054 balanced test conversations.
- Stage 2: 724 weighted train rows representing 282 unique conversations, 32 validation and 36 test rows. Weighted repetition inside training is intentional.
- No normalized full-conversation, user-history or individual user-text overlap was found from either training stage into any supplied validation/test export.
- `eval_kenyan_mixed_test.jsonl` and `stage2_style_test.jsonl` have identical file hashes. They are the same test export, not two independent evaluations.
- The manifest contains 14,558 rows and no group assigned to multiple splits. However, JSONL rows contain messages only, without record IDs or a content-hash-to-record-ID map. Consequently, that grouping cannot be independently joined to the exported texts. Related translations, rewritten variants and semantic duplicates remain unverified.
- The conversational data has no reviewed negative/neutral/positive sentiment labels or high/medium/no-alert labels. Crisis-sensitive records were deferred in the package's source cleaning audit; this set alone cannot establish urgent-detection recall.

The earlier 120-message annotation batch is a starting training-data review, not a representative test set or enough evidence of readiness. Its labels, verified language, source licences and original grouping are still needed. Do not move test rows into training or assign automatic model predictions as human labels.

## Evaluation workflow

1. Recover record-ID/content-hash mapping from the original preprocessing export, or establish and document reviewed translation/scenario groups. Do not infer the mapping from CSV row order. Verify source permission and remove identifiers.
2. Two reviewers independently label participant messages as negative, neutral or positive and confirm English/Kiswahili/Sheng/code-switched language. Resolve disagreements with a third reviewer. Ambiguous or context-dependent items need resolution or documented exclusion. Maintain adequate class and language coverage in all partitions.
3. Use [MindBridge_DistilBERT_Training.ipynb](../notebooks/MindBridge_DistilBERT_Training.ipynb) in a **separate** private Kaggle notebook. It automatically finds exactly one attached `sentiment_labels.csv`, refuses incomplete/conflicting annotations, checks group/text leakage, and preserves train/validation/test splits. No reviewed CSV means no project training.
4. Select a threshold using validation only (initial sweep 0.80–0.90), freeze it, then report per-language class precision/recall/F1, confusion matrices, group-bootstrap 95% intervals and counts. The notebook also compares the binary SST-2 baseline on the same held-out items; explicitly report its inability to predict neutral. An English encoder is not automatically multilingual after adding translated data.
5. Separately review hybrid-risk scenarios with timestamped moods, weekly cycles and text. Record `none`, `medium` or `high` human review priority. Compare keyword-only, behaviour-only, sentiment-only and combined outputs on the same independent scenarios; report false positives/negatives and urgent-subset recall by language. Test model failure and disabled-sentiment modes. Do not derive the human labels from the implemented rules.
6. Review conversation replies on fresh prompts and multi-turn cases, distinct from training and scripted regression examples. Record raw generation versus model-serving fallback/scripted routes, language match, factuality, helpfulness, safety and latency/completion. Freeze the candidate before final tests. Keep the currently rejected repair excluded.
7. After reviewed results meet agreed project criteria, configure the chosen sentiment artifact and hosted conversation service, then test actual Turn.io onboarding, returning users, check-ins, alerts, escalation and bookings. Keep unvalidated sentiment excluded from alert decisions.

## Runnable checks

```powershell
python tools/audit_nlp_data.py --data-zip "PATH\MindBridge_TwoStage_Final(1).zip" --results-zip "PATH\MindBridge_UlizaLlama3_FINAL_TwoStage_Results.zip" --output nlp_audit.json
python tools/check_sentiment_notebook.py
python -m unittest discover -s tools -p "test_*.py"
.\.venv\Scripts\python.exe manage.py test
```

The data auditor uses only Python's standard library and also accepts an unpacked Kaggle input folder for `--data-zip`. The notebook checker requires numpy, pandas and scikit-learn; it executes only helper definitions on fictional rows. Its seven annotation/leakage guard checks and metric checks passed. Both data-audit unit tests passed. All **131 Django tests** passed after the sentiment-gate fix; migration drift checks found no changes. No project classifier was trained and no new GPU model-quality scores are claimed.

Kaggle's existing conversation notebook now contains an October 14 status note and a CPU-only input audit cell. That cell completed with matching counts and overlap findings. Save using Quick Save with outputs; do not Run All. No Hugging Face token or model loading is needed for the audit. The separate private [MindBridge Sentiment - Labels Pending notebook](https://www.kaggle.com/code/jadawalubiri/mindbridge-sentiment-labels-pending/edit) was saved as Version 1 without execution. Its training remains blocked until reviewed data is attached. The existing conversation notebook audit was saved as Version 10 with outputs and its CPU session stopped.

## Code correction

`care/risk.py` now requires the global `SENTIMENT_RISK_ENABLED` switch before recording sentiment evidence and excludes prior sentiment evidence when the switch is off. An injected/mocked result marked `risk_eligible=True` can no longer bypass that setting. Agreement tests explicitly enable experimental sentiment. This strengthens the default exclusion; it does not certify classifier accuracy or enable sentiment in production.
