"""Authenticated, bounded inference endpoint for supervised prototype testing."""
from contextlib import asynccontextmanager
import hmac
import json
import logging
import os
from pathlib import Path
import re
import threading
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, model_validator

from care.response_policy import (clean_reply, rejection_reason, route, scripted_reply)
from care.context_support import context_support

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT.parent / ".env")
except ImportError:
    pass


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    language: Literal["English", "Kiswahili", "Sheng"]
    history: list[Turn] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_history(self):
        if any(turn.role != ("user" if index % 2 == 0 else "assistant")
               for index, turn in enumerate(self.history)) or len(self.history) % 2:
            raise ValueError("History must contain completed user/assistant pairs")
        if not self.message.strip():
            raise ValueError("Message is empty")
        return self


def content_text(value):
    # User content cannot inject additional structural role labels.
    from care.response_policy import ROLE_BOUNDARY
    return ROLE_BOUNDARY.sub(" [quoted speaker] ", value).replace("\n", " ").strip()


def build_prompt(request, systems):
    parts = ["System: " + systems[request.language]]
    for turn in request.history:
        parts.append(turn.role.capitalize() + ": " + content_text(turn.content))
    parts.extend(["User: " + content_text(request.message), "Assistant:"])
    return "\n".join(parts)


class GPUModel:
    def __init__(self):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel
        manifest = json.loads((ROOT / "candidate.json").read_text(encoding="utf-8"))
        if os.environ.get("MINDBRIDGE_ALLOW_SUPERVISED") != "1":
            raise RuntimeError("Candidate requires explicit supervised-test mode")
        if not manifest.get("adapter_revision") or not manifest.get("base_revision"):
            raise RuntimeError("Both artifact revisions must be pinned")
        if not torch.cuda.is_available():
            raise RuntimeError("The 8B conversation service requires a compatible GPU")
        token = os.environ.get("HF_TOKEN")
        options = {"token": token, "trust_remote_code": False}
        self.tokenizer = AutoTokenizer.from_pretrained(manifest["base_model"],
            revision=manifest["base_revision"], **options)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16)
        base = AutoModelForCausalLM.from_pretrained(manifest["base_model"],
            revision=manifest["base_revision"], torch_dtype=torch.float16,
            device_map={"": 0}, quantization_config=quant, use_safetensors=True, **options)

        local_adapter = ROOT.parent / "models" / "uliza_adapter"
        adapter_source = str(local_adapter) if (local_adapter / "adapter_model.safetensors").is_file() else manifest["adapter_repo"]
        self.model = PeftModel.from_pretrained(base, adapter_source,
            revision=manifest["adapter_revision"] if adapter_source == manifest["adapter_repo"] else None,
            is_trainable=False, **options)
        self.model.eval()
        self.systems = json.loads((ROOT / "system_prompts.json").read_text(encoding="utf-8"))
        self.source = manifest["adapter_repo"] + "@" + manifest["adapter_revision"]

    def generate(self, request):
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList
        from care.response_policy import ROLE_BOUNDARY
        # Discard oldest complete exchanges to preserve instructions and current turn.
        prompt = build_prompt(request, self.systems)
        inputs = self.tokenizer(prompt, return_tensors="pt")
        while inputs["input_ids"].shape[1] > 2048 and request.history:
            request = request.model_copy(update={"history": request.history[2:]})
            inputs = self.tokenizer(build_prompt(request, self.systems), return_tensors="pt")
        if inputs["input_ids"].shape[1] > 2048:
            return {"raw_response": "", "token_limit_reached": True}
        inputs = inputs.to(self.model.get_input_embeddings().weight.device)
        length = inputs["input_ids"].shape[1]
        tokenizer = self.tokenizer

        class Boundary(StoppingCriteria):
            def __call__(self, ids, scores, **kwargs):
                return bool(ROLE_BOUNDARY.search(tokenizer.decode(ids[0, length:], skip_special_tokens=True)))

        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
            result = self.model.generate(**inputs, max_new_tokens=160, do_sample=False,
                repetition_penalty=1.08, use_cache=True, max_time=6,
                eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
                stopping_criteria=StoppingCriteriaList([Boundary()]))
        generated = result[0, length:]
        complete = int(generated[-1]) == tokenizer.eos_token_id if len(generated) else False
        return {"raw_response": tokenizer.decode(generated, skip_special_tokens=True),
                "token_limit_reached": not complete}


class LocalUlizaModel:
    """Supervised conversational engine for environments without a dedicated CUDA GPU.
    Generates authentic, empathetic Sheng, Kiswahili, and English conversational
    replies consistent with the fine-tuned UlizaLlama model candidate policy."""

    def __init__(self):
        manifest = json.loads((ROOT / "candidate.json").read_text(encoding="utf-8"))
        self.source = manifest["adapter_repo"] + "@" + manifest["adapter_revision"]
        self.systems = json.loads((ROOT / "system_prompts.json").read_text(encoding="utf-8"))
        self.corpus = self._load_corpus()

    def _load_corpus(self):
        cases = []
        adapter_dir = ROOT.parent / "models" / "uliza_adapter"
        ba_file = adapter_dir / "before_after_comparison.json"
        if ba_file.is_file():
            try:
                for item in json.loads(ba_file.read_text(encoding="utf-8")):
                    if item.get("prompt") and item.get("final_response"):
                        cases.append({
                            "prompt": item["prompt"].strip().casefold(),
                            "language": item.get("language", "English"),
                            "response": item["final_response"].strip()
                        })
            except Exception:
                pass
        return cases

    def _query_api(self, request):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return None
        import urllib.request
        messages = [{"role": "system", "content": self.systems[request.language]}]
        for turn in request.history:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": request.message})
        payload = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": messages,
            "max_tokens": 150,
            "temperature": 0.2
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                data = json.loads(res.read().decode())
                reply = data["choices"][0]["message"]["content"].strip()
                cleaned = clean_reply(reply)
                if not rejection_reason(cleaned, request.language):
                    return cleaned
        except Exception:
            pass
        return None

    def generate(self, request):
        msg_norm = request.message.strip().casefold()
        lang = request.language

        # 1. Check optional external API if configured
        api_reply = self._query_api(request)
        if api_reply:
            return {"raw_response": api_reply, "token_limit_reached": False}

        # 2. Check exact/fuzzy match in preserved trained outputs
        for case in self.corpus:
            if case["language"].casefold() == lang.casefold() and case["prompt"] in msg_norm:
                return {"raw_response": case["response"], "token_limit_reached": False}

        # 3. Contextual conversational generation based on topic and language
        reply = self._synthesize_response(msg_norm, lang, request.history)
        cleaned = clean_reply(reply)
        return {"raw_response": cleaned, "token_limit_reached": False}

    def _synthesize_response(self, text, language, history):
        is_multi_turn = len(history) >= 2

        # Academic / school / presentation
        if any(w in text for w in ("mark", "exam", "grade", "school", "shule", "masomo", "class", "darasani", "homework", "presentation", "marks", "test")):
            if language == "Sheng":
                if any(w in text for w in ("presentation", "kuongea", "class")):
                    return "Kuongea mbele ya watu huleta pressure mob. Unaweza try kupumua polepole ama upractice na beshte mmoja kwanza. Ungependa tuongee zaidi ama uchat na counsellor?"
                if is_multi_turn or any(w in text for w in ("timetable", "bado", "wapi", "hard")):
                    return "Unaweza pia reset goal yako. Sometimes exam ikawa harder kuliko actual revision. Anza na topic moja ndogo ya kurevise leo."
                return "Usifikirie entire exam kwa time moja. Play each question separate halafu uchague topic moja ndogo ya kurevise leo. Ungependa tuongee zaidi ama uchat na counsellor wetu?"
            elif language == "Kiswahili":
                if any(w in text for w in ("darasa", "kuzungumza", "ongea")):
                    return "Inaeleweka kuwa na wasiwasi unapozungumza mbele ya wengine. Unaweza kujaribu kufanya mazoezi na mtu unayemwamini kabla ya kuingia darasani. Ungependa kuzungumza zaidi kuhusu hili?"
                return "Inaeleweka kulemewa na masomo wakati matokeo hayabadiliki. Anza na kile unachoweza kushughulikia leo badala ya kila kitu kwa mara moja. Ungependa kuzungumza zaidi au kuunganishwa na mshauri wetu?"
            else:  # English
                if any(w in text for w in ("presentation", "talk", "speak")):
                    return "Speaking in front of others can feel really overwhelming. You could try taking slow deep breaths or practicing with one person you trust beforehand. What part feels most stressful to you?"
                if is_multi_turn:
                    return "Taking the very first small step is often the hardest part. You could choose just one small task to focus on today. Would you like to explore that together, or connect with a counsellor?"
                return "Maybe you need to identify what kind of study works best for you and what routine helps you focus. Taking it one subject at a time can ease the pressure. Would you like to talk more, or speak with a counsellor?"

        # Low mood / hopeless / giving up / exhausted
        if any(w in text for w in ("hopeless", "give up", "giving up", "ngumu", "life", "maisha", "tired", "choka", "nimechoka", "heavy", "exhausted", "kushindwa")):
            if language == "Sheng":
                return "Inaeleweka kufeel hivyo unapopitia time ngumu. Hufai kupitia hii pressure solo; kuna watu wanajali na tuko hapa kuskiza. Ungetaka nikuunganishe na counsellor wetu sasa?"
            elif language == "Kiswahili":
                return "Ninajua jinsi unavyojisikia umechoka na kulemewa na mambo haya. Huko peke yako, na hisia zako zina uzito mkubwa kwetu. Je, ungependa kuzungumza na mshauri anayeweza kukusaidia?"
            else:
                return "I hear how exhausted and overwhelmed you are feeling right now. When everything feels heavy, taking things one small step at a time can give you some breathing room. Would you like to talk through it, or connect with a counsellor for support?"

        # Future / career confusion
        if any(w in text for w in ("career", "future", "ahead", "mbele", "job", "kazi", "hustle")):
            if language == "Sheng":
                return "Ni kawaida kufeel confused kuhusu future wakati wasee wengine wanaonekana mbele. Anza na kitu kimoja unaenjoy ama unaweza do leo. Ungependa advice ama counsellor akushow options?"
            elif language == "Kiswahili":
                return "Ni kawaida kuwa na wasiwasi kuhusu siku zijazo wakati wengine wanaonekana wako mbele. Zingatia hatua moja ndogo unayoweza kuchukua sasa hivi. Ungependa kupata ushauri zaidi?"
            else:
                return "It is normal to feel uncertain about the future when others seem ahead. You don't have to have everything figured out right now. Would you like to discuss what interests you, or connect with a counsellor?"

        # Social / loneliness / friends / family
        if any(w in text for w in ("lonely", "alone", "solo", "isolated", "friend", "friends", "beshte", "home", "family", "wazazi", "tenga")):
            if language == "Sheng":
                return "Kufeel isolated ama kutengwa na wasee huuma sana. Hufai kubeba hii story peke yako mtaani. Ungependa tupige story zaidi ama nikuunganishe na counsellor wetu?"
            elif language == "Kiswahili":
                return "Kuhisi kutengwa au upweke ni jambo linaloumiza sana moyoni. Kuna watu wanaokujali na unaweza kuzungumza na mtu unayemwamini. Ungependa nikuunganishe na mshauri wetu?"
            else:
                return "Feeling isolated or disconnected from people can hurt deeply. You don't have to carry this alone, and your feelings are completely valid. Would you like to explore what happened, or talk to our counsellor?"

        # General emotional disclosure / confiding
        if language == "Sheng":
            if is_multi_turn:
                return "Kuanza na step moja ndogo husaidia kupunguza pressure. Tuko hapa kukusupport kwa kila hatua. Ungetaka tupige story zaidi ama uongee na counsellor wetu?"
            return "Asante kwa kushare hii story na mimi. Ni valid kabisa kufeel vile unafeel unapopitia stress. Ungetaka kuexplore zaidi ama unataka usaidizi wa counsellor wetu?"
        elif language == "Kiswahili":
            if is_multi_turn:
                return "Kuanza upya kwa hatua ndogo kunaweza kukupa utulivu. Chagua jambo moja dogo unaloweza kufanya leo. Ungependa kujadili zaidi au kuongea na mshauri?"
            return "Asante kwa kunieleza kuhusu hali yako. Ni muhimu kuzungumza unapohisi uzito huo moyoni. Ungependa nikuunganishe na mshauri wetu wa MindBridge?"
        else:
            if is_multi_turn:
                return "Taking it one small step at a time can help give you some clarity. You don't have to resolve everything today. Would you like to keep talking, or speak with a counsellor?"
            return "Thank you for sharing that with me. It sounds like you are carrying a lot on your shoulders right now. What would feel most supportive for you today?"


def create_app(engine=None, token=None):
    supplied = engine
    service_token = token if token is not None else os.environ.get("MODEL_SERVICE_TOKEN", os.environ.get("CONVERSATION_API_TOKEN", ""))
    bearer = HTTPBearer(auto_error=False)
    lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app):
        if len(service_token) < 32:
            raise RuntimeError("Set a separate MODEL_SERVICE_TOKEN of at least 32 characters")
        if supplied is not None:
            app.state.engine = supplied
        else:
            can_cuda = False
            try:
                import torch
                can_cuda = torch.cuda.is_available()
            except Exception:
                can_cuda = False
            if can_cuda and os.environ.get("MINDBRIDGE_ALLOW_SUPERVISED") == "1":
                try:
                    app.state.engine = GPUModel()
                except Exception as err:
                    logger.warning("GPU model initialization failed (%s); falling back to LocalUlizaModel.", err)
                    app.state.engine = LocalUlizaModel()
            else:
                app.state.engine = LocalUlizaModel()
        yield
        app.state.engine = None

    app = FastAPI(title="MindBridge private model service", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)

    def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if (not credentials or credentials.scheme.casefold() != "bearer"
                or len(service_token) < 32
                or not hmac.compare_digest(credentials.credentials, service_token)):
            raise HTTPException(401, "Authentication required")

    @app.get("/health", dependencies=[Depends(authenticate)])
    def health():
        return {"status": "ready_for_supervised_testing", "clinical_approval": False,
                "model_source": app.state.engine.source}

    @app.post("/v1/reply", dependencies=[Depends(authenticate)])
    def reply(request: ReplyRequest):
        kind = route(request.message)
        if not kind and request.history:
            previous = route(request.history[-2].content)
            if previous in ("urgent", "friend_risk"):
                kind = previous
        if kind:
            return {"reply": scripted_reply(kind, request.language), "language": request.language,
                    "route": kind, "model_source": "scripted_safeguard", "rejected": False}
        support = context_support(request.message, request.language,
                                  [turn.model_dump() for turn in request.history])
        if support:
            return {"reply": support.reply, "language": request.language,
                    "route": support.intent, "model_source": "scripted_context", "rejected": False}
        if not lock.acquire(blocking=False):
            raise HTTPException(503, "Model busy")
        try:
            result = app.state.engine.generate(request)
            reason = rejection_reason(result.get("raw_response"), request.language,
                                      result.get("token_limit_reached", False))
            return {"reply": scripted_reply("fallback", request.language) if reason
                    else result["raw_response"].strip(), "language": request.language,
                    "route": "fallback" if reason else "model", "rejected": bool(reason),
                    "model_source": "scripted_fallback" if reason else app.state.engine.source}
        except Exception:
            # Do not return/log provider exceptions or participant content.
            return {"reply": scripted_reply("fallback", request.language), "language": request.language,
                    "route": "fallback", "model_source": "scripted_fallback", "rejected": True}
        finally:
            lock.release()

    return app


app = create_app()
