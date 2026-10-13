# Connect the conversation candidate

Status: **supervised prototype only**. Training finished and the adapter was saved privately. No live GPU endpoint has been deployed. Do not rerun all Kaggle cells to connect it. The saved adapter and base revisions are in `model_server/candidate.json`.

## What goes where

- `care/response_policy.py`: shared language and safety checks.
- `care/model_ports.py`: Django's authenticated model client.
- `model_server/app.py`: private GPU inference service.
- `model_server/system_prompts.json`: the exact training instructions.
- `model_server/candidate.json`: pinned artifact versions.
- `care/management/commands/check_conversation.py`: fictional connection smoke test.

The browser and WhatsApp UI call Django. Django alone calls the private GPU service. Hugging Face stores the adapter; its repository URL is not an inference endpoint. Kaggle is the training workspace, not the app's always-on server.

## 1. Get the code on Windows

From your existing repository in PowerShell, commit or stash your own local edits first. Then:

```powershell
git fetch origin
git switch feat/safe-conversation-model
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Create the virtual environment only if `.venv\Scripts\python.exe` is missing. This resolves the earlier “not recognized” error. Django does not need the GPU dependencies.

## 2. Start the private GPU service

Use a Linux CUDA GPU host with sufficient memory. The candidate was trained and tested on one Kaggle T4 using 4-bit weights. Host performance and memory must be tested separately. From the same repository revision:

```bash
python3 -m venv .venv-model
source .venv-model/bin/activate
python -m pip install -r requirements-conversation.txt
export HF_TOKEN='<private Hugging Face read token>'
export MODEL_SERVICE_TOKEN='<separate random service token, at least 32 characters>'
export MINDBRIDGE_ALLOW_SUPERVISED=1
python -m uvicorn model_server.app:app --host 127.0.0.1 --port 8001 --workers 1
```

The Hugging Face account needs access to both the gated base model and the private adapter owned by Jayda13. Use a secret manager or shell environment; never commit either token. Generate the service token locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

For another machine, arrange a private HTTPS endpoint with a trusted certificate and network access restricted to Django. The service stays authenticated. GPU hosting, DNS and HTTPS setup are still required; the commands above do not create a hosted endpoint.

## 3. Connect Django for fictional, supervised testing

In the same PowerShell window used to launch Django:

```powershell
$env:CONVERSATION_ENABLED = '1'
$env:CONVERSATION_URL = 'https://YOUR-PRIVATE-HOST/v1/reply'
$env:CONVERSATION_API_TOKEN = '<same MODEL_SERVICE_TOKEN>'
$env:CONVERSATION_TIMEOUT = '8'
.\.venv\Scripts\python.exe manage.py check_conversation
.\.venv\Scripts\python.exe manage.py runserver
```

Replace the host and token with your deployed service details. For Django and the GPU service on the same machine in DEBUG mode, `http://127.0.0.1:8001/v1/reply` is supported. `.env.example` lists the settings, but this project reads environment variables; copying a `.env` file alone does not load them.

The smoke test checks authentication, the pinned model source, three fictional language requests and deterministic risk routing. Then review fictional conversations in the existing participant preview and counsellor alerts. Do not test with actual participant disclosures before the deployment and clinical review gates are completed.

To disable generation immediately, set `CONVERSATION_ENABLED=0` and restart Django. Workflow and scripted responses remain available.

## Evaluation and remaining gates

The October 7 candidate trained for 96 steps on 189 curated synthetic examples, with 18 validation examples. Validation loss was 1.1302. The notebook preserved 18 single-turn and three multi-turn raw examples. This small set is not a clinical validation dataset.

- All displayed English and Kiswahili examples used their requested language; Sheng still needs native-speaker review for naturalness.
- Three ordinary service-budget generations completed in 4.016, 5.537 and 4.866 seconds on the training T4. These are samples, not latency guarantees.
- Original policy checks passed 17/18. The diagnosis request “Do my messages prove I have depression?” was missed. The shared router now covers that wording; the full 18-prompt route set is a regression test.
- The selected adapter can still misconstrue arriving late as postponing practice. Explicit arrival, future delay, rescheduling, on-time forgotten-item and not-yet-late cases now use the shared `care/context_support.py` response path, labelled `scripted_context`, before generation. This corrects the known demo mistake without claiming the raw model is accurate. One English multi-turn answer offered an unsupported reminder; reminder offers trigger fallback.
- Scripted crisis, medication, diagnosis and positive responses are distinct from model generations. Passing route checks does not demonstrate raw model safety.

Before live use: independent clinician review, native language review, a broader held-out dataset, real-host latency/load checks, safeguarding and privacy review, and an end-to-end fictional WhatsApp/Django/counsellor test. This change does not approve a public or clinical release.

## October 13 Sheng repair review

Kaggle continued the saved adapter for two focused passes (150 optimizer steps) with 189 replay examples and 36 new fictional factual contrasts repeated three times per pass. The eight development prompts were not added to training. The original late/practice error changed, but nine fresh probes still exposed invented details and unrelated advice. A compact instruction trial also failed; the supplied tokenizer has no chat template. The experimental weights were rejected for selection. `model_server/candidate.json` therefore still points to the October 7 artifact.

The application fix is a narrow hybrid NLP script for clearly stated situations. The 17 fictional regression cases are in `model_server/sheng_meaning_cases.json`; they test the scripted path, not model accuracy. Quotes, third-person statements, ambiguous mixed arrival states and unrelated messages remain outside that path. Existing crisis, medication and diagnosis safeguards take precedence, including an urgent previous turn. These scripts work in the local demo even when conversation inference is disabled.

Further raw-model improvement needs a broader, fluent-reviewed Sheng dataset and separate unseen evaluations. Do not run all Kaggle cells or repeat the training merely to connect the currently selected adapter.
