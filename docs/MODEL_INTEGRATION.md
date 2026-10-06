# Model integration

## Sentiment baseline

`classify_note(text)` now runs local DistilBERT inference when enabled. The English
baseline is `distilbert/distilbert-base-uncased-finetuned-sst-2-english`, pinned to
revision `714eb0fa89d2f80546fda750413ed43d93601a13` (verified 6 October 2026).

This is an SST-2 positive/negative sentiment baseline, not a mental-health risk
classifier, a neutral classifier, or the conversation model. Kiswahili, Sheng
and code-switched scores are unvalidated. It is not fine-tuned on MindBridge data.
See the [model card](https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english).

Messages and attached mood notes store label, confidence, model/revision source
and whether the score was eligible for risk checks. The participant profile
labels baseline scores as excluded from risk by default. Confidence is model
class probability, not probability of suicide or a calibrated clinical score.

## Windows local setup

Stop Django first. In the project PowerShell window:

```powershell
git pull --ff-only origin feat/full-stack-care-workspace
.\.venv\Scripts\python.exe -m pip install "torch>=2.6,<3" --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-sentiment.txt
.\.venv\Scripts\python.exe manage.py migrate
$env:SENTIMENT_ENABLED="1"
$env:SENTIMENT_RISK_ENABLED="0"
.\.venv\Scripts\python.exe manage.py check_sentiment --download
.\.venv\Scripts\python.exe manage.py runserver
```

The first download needs internet access and roughly 270 MB for model weights
plus tokenizer files. CPU inference needs no GPU or Hugging Face token for this
public model. Dependency installation needs additional disk space. Variables
apply to this PowerShell session; `.env` is not loaded automatically. Keep
`DJANGO_DEBUG=1` for the local preview.

`check_sentiment` without `--download` runs two fictional smoke checks. Participant
text is not sent to Hugging Face: only setup fetches model artifacts. Chat
inference reads cached weights with `local_files_only=True`, uses safetensors
and does not execute repository-supplied model code.

For a UI check, finish demo onboarding, enter mood 3 and send an English note.
Open the participant profile to see sentiment, score, source and baseline status.
Previous messages are not automatically rescored. Replies stay scripted until
the conversation model is connected.

## Hybrid integration testing

`SENTIMENT_RISK_ENABLED=0` stores scores without adding sentiment evidence. For
fictional integration testing only, set it to `1` and restart. A negative score
at confidence >=0.85 then supplies one layer; an active Tier 2 keyword supplies
another. Tier 1 and the documented mood/disengagement exceptions remain
independent. Restore `0` after testing this unvalidated baseline. See
[RISK_CHECKS.md](RISK_CHECKS.md).

Changing models requires named `negative`/`neutral`/`positive` labels,
`SENTIMENT_MODEL` and an explicit `SENTIMENT_REVISION`, then download and restart.
Generic `LABEL_0` mappings are rejected rather than guessed. A local model folder
is also accepted through `SENTIMENT_MODEL`.

Loading is lazy and cached per process; a failed load stays unavailable until
restart. Missing dependencies/weights and inference errors return no prediction;
keyword and mood alerts continue. Logs omit participant text. Sentiment inputs
are truncated to 512 tokens; keywords still check the full stored input. Initial
inference can take longer while CPU weights load.

## Validation and remaining work

All 69 Django tests passed on 6 October 2026 (14 new sentiment checks); migration
consistency passed. Real CPU inference produced positive/negative labels for the
fictional command examples. These are implementation checks, not accuracy
measurements. Tested runtime: Transformers 4.57.6, PyTorch 2.14.1+cpu,
Python 3.12/Linux. Windows setup still needs verification.

Issue #5 stays open for local setup, evaluated artifact selection and acceptance.
Issue #6 covers labelled held-out English, Kiswahili, Sheng and code-switched
evaluation, threshold calibration and false/missed alerts. Fine-tuning and
multilingual coverage remain unfinished.

## Conversation model

`generate_response(text, context)` still returns `None`. The separately trained
conversation model needs its own evaluated artifact and adapter (issue #4).
Recent context is supplied, but scripted replies remain. Sentiment inference
does not generate WhatsApp replies.
