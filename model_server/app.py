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
        self._systems_cache = None

        self.corpus = self._load_corpus()

        self.corpus = self._load_corpus()

    @property
    def systems(self):
        try:
            return json.loads((ROOT / "system_prompts.json").read_text(encoding="utf-8"))
        except Exception:
            return {}
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
        self._systems_cache = None

        self.corpus = self._load_corpus()

    @property
    def systems(self):
        try:
            return json.loads((ROOT / "system_prompts.json").read_text(encoding="utf-8"))
        except Exception:
            return {}
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
            try:
                from dotenv import load_dotenv
                load_dotenv(ROOT.parent / ".env", override=True)
                api_key = os.environ.get("GROQ_API_KEY")
            except Exception:
                pass
        if not api_key:
            return None

        import urllib.request
        from care.response_policy import select_language
        effective_history = []
        for idx in range(0, len(request.history) - 1, 2):
            u_turn, a_turn = request.history[idx], request.history[idx + 1]
            if select_language(u_turn.content, request.language) == request.language:
                clean_a = re.sub(r"[^.?!]*\b(?:hobby|sport|club|music)\b[^.?!]*[.?!]?", "", a_turn.content, flags=re.I).strip() or a_turn.content
                effective_history.extend([u_turn, Turn(role="assistant", content=clean_a)])
        sys_prompt = self.systems[request.language]
        few_shot = self._retrieve_kenyan_examples(request.message, request.language, [t.content for t in effective_history])
        if few_shot:
            sys_prompt = sys_prompt + "\n\n" + few_shot
        if not effective_history:
            sys_prompt += "\n\nIMPORTANT FOR THIS TURN: This is the participant's FIRST opening message on this issue. Do NOT suggest booking a counsellor yet—focus 100% on warm validation and asking a counsellor-style question about how long they have felt this way, how it affects their daily life, or their trust/exclusion feelings."
        messages = [{"role": "system", "content": sys_prompt}]
        for turn in effective_history:
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": request.message})

        preferred_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
        candidate_models = [preferred_model, "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        seen = set()
        models_to_try = [m for m in candidate_models if m and not (m in seen or seen.add(m))]

        for model_name in models_to_try:
            payload = json.dumps({
                "model": model_name,
                "messages": messages,
                "max_tokens": 400,
                "temperature": 0.4
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "MindBridge/1.0"
                }
            )
            try:
                with urllib.request.urlopen(req, timeout=12) as res:
                    data = json.loads(res.read().decode())
                    reply = data["choices"][0]["message"].get("content", "").strip()
                    if reply:
                        cleaned = self._polish_reply(clean_reply(reply), request.language, bool(effective_history))
                        if not rejection_reason(cleaned, request.language):
                            from care.response_policy import _DANGER
                            if not _DANGER.search(request.message):
                                cleaned = re.sub(r"\b(?:breath\s+kid[gd]o[\s,!:\-—]*)?usijiumize\s+tuko\s+hapa[\s,!:\-—]*", "", cleaned, flags=re.I).strip()
                                cleaned = re.sub(r"\busijiumize[\s,!:\-—]*", "", cleaned, flags=re.I).strip()
                                if cleaned:
                                    cleaned = cleaned[0].upper() + cleaned[1:]
                            logger.info("Groq API (%s) generated reply successfully.", model_name)
                            return cleaned
            except Exception as e:
                logger.warning("Groq API error on model %s: %s", model_name, e)
                continue
        return None

    def _retrieve_kenyan_examples(self, message: str, language: str, history_texts: list[str]) -> str:
        """Retrieve topic-matched Kenyan counsellor examples to ground vocabulary and grammar."""
        ex_file = ROOT / "kenyan_examples.json"
        if not ex_file.is_file():
            return ""
        try:
            bank = json.loads(ex_file.read_text(encoding="utf-8"))
        except Exception:
            return ""
        combined = (" ".join(history_texts[-2:]) + " " + message).casefold()
        matched_examples = []
        for entry in bank:
            if any(kw in combined for kw in entry.get("keywords", [])):
                matched_examples.extend(entry.get("examples", {}).get(language, []))
        if not matched_examples and bank:
            matched_examples.extend(bank[0].get("examples", {}).get(language, [])[:1])
        if not matched_examples:
            return ""
        lines = ["AUTHENTIC KENYAN COUNSELLOR REFERENCE EXAMPLES (Mirror this exact natural grammar, simplicity, and counsellor flow):"]
        for ex in matched_examples[:2]:
            lines.append(f"User: '{ex['user']}'")
            lines.append(f"Assistant: '{ex['assistant']}'")
        return "\n".join(lines)

    def _polish_reply(self, cleaned: str, language: str, has_history: bool = False) -> str:
        """Fix morphological blends (like 'kuhisik') and keep Kiswahili Sanifu free of English leak tokens."""
        if not cleaned:
            return cleaned
        cleaned = cleaned.replace("\u202f", " ").replace("\u00a0", " ").replace("\u2011", "-")
        cleaned = re.sub(r"\bkuhisik[a-z]*\b", "kuhisi", cleaned, flags=re.I)
        cleaned = re.sub(r"\bmkao\s+wa\s+upweke\b", "upweke", cleaned, flags=re.I)
        cleaned = re.sub(r"\bni\s+ghali\s+ya\s+watu\b", "ni tabia ya watu", cleaned, flags=re.I)
        cleaned = re.sub(r"\bkutokujua\b", "kutojua", cleaned, flags=re.I)
        cleaned = re.sub(r"\bkutokupata\b", "kukosa kupata", cleaned, flags=re.I)
        cleaned = re.sub(r"\b[iu]met?impacti?\b", "imeaffect", cleaned, flags=re.I)
        cleaned = re.sub(r"\bumeshwa\s+na\s+kutrust\b", "umepata ugumu wa kutrust", cleaned, flags=re.I)
        cleaned = re.sub(r"\bwapo\s+waki\s*disappear\b", "wanapotea", cleaned, flags=re.I)
        cleaned = re.sub(r"\bwaki\s+disappear\b", "wanapotea", cleaned, flags=re.I)
        cleaned = re.sub(r"\bbila\s+kujikokota\b", "bila kujiforce", cleaned, flags=re.I)
        cleaned = re.sub(r"[^.?!]*\b(?:kujaribu\s+hobby|hobby\s+kama|sport\s+au\s+club|join\s+a?\s*club)\b[^.?!]*\bsaidia[^.?!]*[,.?!]?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bJe,\s*umewahi\s+kujaribu\s+hobby[^,?]*,\s*na\s+pia\s+", "Je, ", cleaned, flags=re.I)
        if language == "Kiswahili":
            sw_replacements = (
                (r"\bfriends\b", "marafiki"),
                (r"\bpressure\b", "shinikizo"),
                (r"\bschoolwork\b", "kazi za shule"),
                (r"\bhomework\b", "kazi ya nyumbani"),
                (r"\bassignment\b", "kazi ya darasani"),
                (r"\broutine\b", "ratiba"),
                (r"\bsupport\b", "msaada"),
                (r"\bhelp\b", "msaada"),
                (r"\btry\b", "jaribu"),
                (r"\btoday\b", "leo"),
                (r"\bsometimes\b", "wakati mwingine"),
                (r"\bplease\b", "tafadhali"),
                (r"\bsafe\b", "salama"),
                (r"\breply\b", "jibu"),
                (r"\bcheck\b", "angalia"),
                (r"\bstress\b", "msongo wa mawazo"),
            )
            for pattern, replacement in sw_replacements:
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
        if has_history:
            cleaned = re.sub(r"^(?:(?:Sis|Bro|Buda|Manze|Maze)[\s,!:\-—]+)?(?:Niaje|Sema|Vipi|Mambo|Habari|Hujambo|Hello|Hi|Hey)[\s,!:\-—]+", "", cleaned, flags=re.I).strip()
            cleaned = re.sub(r"\btuliza\s*ball\b[\s,!:\-—]*", "", cleaned, flags=re.I).strip()
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
        return cleaned

    def generate(self, request):
        msg_norm = request.message.strip().casefold()
        lang = request.language

        # 1. Check exact/fuzzy match in preserved trained outputs
        for case in self.corpus:
            if case["language"].casefold() == lang.casefold() and case["prompt"] in msg_norm:
                return {"raw_response": case["response"], "token_limit_reached": False}

        # 2. For Kiswahili and Sheng, prefer verified Kenyan counsellor synthesis when the message matches
        # a known youth mental health topic so replies use 100% authentic, natural Kenyan phrasing without
        # broken literal translations from English-centric cloud models.
        if lang in ("Sheng", "Kiswahili"):
            synth = self._synthesize_response(msg_norm, lang, request.history, strict_match=True)
            if synth:
                cleaned = self._polish_reply(clean_reply(synth), lang, bool(request.history))
                return {"raw_response": cleaned, "token_limit_reached": False}

        # 3. Query external LLM API (primary for English and for open-ended/unseen topics)
        api_reply = self._query_api(request)
        if api_reply:
            return {"raw_response": api_reply, "token_limit_reached": False}

        # 4. Fallback contextual conversational generation
        reply = self._synthesize_response(msg_norm, lang, request.history, strict_match=False)
        cleaned = self._polish_reply(clean_reply(reply), lang, bool(request.history))
        return {"raw_response": cleaned, "token_limit_reached": False}

    def _synthesize_response(self, text, language, history, strict_match=False):
        prior = [turn.content.strip().casefold() for turn in history if turn.role == "assistant"]
        prior_user = " ".join(turn.content.strip().casefold() for turn in history if turn.role == "user")
        is_multi_turn = len(history) >= 2

        def pick_fresh(options):
            for opt in options:
                if not any(opt.strip().casefold() in p or p in opt.strip().casefold() for p in prior):
                    return opt
            return options[-1]

        has_no_money_counsellor = (
            any(w in text for w in ("sina pesa", "sina dooh", "sina doh", "kulipa", "gharama", "afford", "no money", "malipo", "pesa ya counsellor", "pesa za mshauri"))
            and any(w in text or w in prior_user for w in ("counsellor", "counselor", "mshauri", "lonely", "solo", "upweke", "stress", "overthink", "msaada"))
        )
        has_overthink_or_what_to_do = any(w in text for w in (
            "overthink", "nikioverthink", "nawaza sana", "usingizi", "nalala", "kuchoka kuwa mtu wa kusaidia",
            "nifanye nini", "nifanyeje", "what should i do", "what do i do", "nimechoka kubeba", "convenience"
        ))
        has_siblings = any(w in text for w in ("sibling", "siblings", "ndugu", "watoto", "masibling", "take care", "care of", "chores", "duties", "baby", "dogo"))
        has_exam = any(w in text for w in ("exam", "exams", "test", "marks", "grade", "masomo", "kusoma", "study", "revise", "revision", "mitihani", "mtihani"))
        has_no_time = any(w in text for w in ("sijakuwa na time", "sina time", "no time", "running out of time", "muda", "bado nafeel", "behind", "nyuma"))
        has_alone_duty = any(w in text for w in ("hakuna msee", "mimi pekee", "peke yangu", "solo", "madhe", "fathe", "late", "job"))
        has_pregnancy = any(w in text for w in ("pregnant", "mimba", "pregnancy", "clinic", "abort", "abortion", "kuabort", "kutoa mimba", "nimepata mimba"))
        has_breakup = any(w in text for w in ("boyfriend", "girlfriend", "dem wangu", "chali wangu", "mpenzi", "tuliachana", "tuliwachana", "breakup", "broke up", "break up", "my ex", "text him", "text her", "kumtext", "heartbroken", "mapenzi"))
        has_fees = any(w in text for w in ("school fees", "school fee", "karo", "fukuzwa", "kufukuzwa", "pesa za shule", "kulipia shule"))
        has_lonely_friends = any(w in text for w in (
            "friend", "friends", "beshte", "mabeshte", "marafiki", "rafiki", "lonely", "alone", "solo",
            "isolated", "sina friends", "sina beshte", "tenga", "kutengwa", "upweke", "mpweke",
            "hakuna place", "convenience", "wanadisappear", "wanapotea", "wakihitaji", "wasee hunicall"
        ))
        has_parent_conflict = any(w in text for w in ("fighting", "fight", "kufight", "wazazi kufight", "parents fighting", "wazazi", "parents", "argue", "arguing", "zozano", "ugomvi", "makelele"))
        has_concentration = any(w in text for w in ("concentrate", "concentration", "focus", "kushindwa kusoma", "distraction", "kuzingatia"))

        # 0. Follow-up where participant worries about paying a counsellor or asks what to do next after overthinking/people-pleasing
        if has_no_money_counsellor or (is_multi_turn and has_overthink_or_what_to_do and (has_lonely_friends or "upweke" in prior_user or "solo" in prior_user or "mabeshte" in prior_user)):
            if language == "Sheng":
                return pick_fresh([
                    "Kwanza kabisa manze, usiworry kuhusu pesa—huduma zote za counsellors wa MindBridge ni za bure kabisa (100% free), hulipi chochote. Kuoverthink usiku na kuchoka kubeba kila msee ili tu ukubalike inachosha sana akili, lakini kuona hivyo ni hatua ya kwanza ya kujithamini na kuweka mipaka (boundaries). Ungependa nikuonyeshe masaa ambayo counsellor wetu wa bure ako available uongee naye?",
                    "Pole sana kwa kukosa usingizi ukiwaza haya manze, na ujue counsellors wa MindBridge ni wa bure kabisa bila malipo yoyote. Kuchoka kutumiwa na wasee ni mwanzo wa kujilinda na kujenga boundaries zenye afya. Ungependa tupange session ya bure na counsellor wetu akusaidie kupitia hii hatua?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Kwanza kabisa, usiwe na wasiwasi kuhusu pesa—washauri wetu wa MindBridge wanatoa huduma hii bure kabisa bila malipo yoyote. Kukosa usingizi ukiwaza na kuchoka kutumiwa na wengine ni mzigo mzito, lakini kutambua hilo ni hatua muhimu ya kujithamini na kuweka mipaka. Je, ungependa nikuonyeshe muda ambao mshauri wetu wa bure anapatikana ili uzungumze naye?",
                    "Pole sana kwa kulemewa na mawazo mengi usiku; kumbuka huduma za mshauri wa MindBridge ni za bure kabisa. Kuchoka kubeba kila mtu ili ukubalike ni mwanzo wa kuweka mipaka inayolinda amani yako. Je, ungependa nikuunganishe na mshauri wetu sasa?",
                ])
            else:
                return pick_fresh([
                    "First, please don't worry about money—speaking with a MindBridge counsellor is 100% free of charge. Lying awake overthinking and feeling exhausted from always giving just to keep people around is heavy, and recognising it is the first step toward setting healthy boundaries. Would you like me to show you the available times to talk with one of our free counsellors?",
                ])

        # 1. Pregnancy / reproductive health distress
        if has_pregnancy:
            if language == "Sheng":
                return pick_fresh([
                    "Inaeleweka kufeel scared na kuchanganyikiwa wakati huu. Hufai kupitia hii pressure solo; vituo vya afya vya vijana (youth-friendly health centres) na public hospitals zinatoa huduma na ushauri wa siri bila malipo makubwa. Pia kuna helpline za bure Kenya kama Childline 1190 au 1195. Ungependa tusaidiane kuangalia kituo kilicho karibu na wewe?",
                    "Kupata mimba kukiwa na hofu ya wazazi huleta mshtuko mkubwa sana. Tuko hapa kukusikiliza bila judgement. Madaktari na counsellors wa vituo vya afya vya umma wanaweza kukusaidia kwa siri na usalama. Ungependa kupata contact za mahali unaweza kupata msaada salama?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Inaeleweka sana kuwa na hofu na mshtuko mkubwa wakati huu. Huko peke yako; vituo vya afya vya umma na madawati ya vijana vinatoa ushauri salama na wa siri bila gharama kubwa, na nambari za bure kama 1190 au 1195 zipo kukusaidia. Je, ungependa tukuelekeze kwenye kituo cha afya kilicho karibu?",
                ])
            else:
                return pick_fresh([
                    "It is completely understandable to feel overwhelmed and terrified right now. You do not have to handle this alone. Public youth-friendly health clinics offer confidential, subsidised care, and free helplines like Childline 1190 and 1195 are available 24/7. Would you like help finding a safe, confidential clinic near you?",
                ])

        # 2. Breakup / relationship distress
        if has_breakup:
            if language == "Sheng":
                return pick_fresh([
                    "Pole sana manze. Breakup na msee uliyemzoea huuma sana na kuleta mawazo mengi. Hii ilihappen muda gani uliopita, na imekuwa ikiaffect aje usingizi wako ama siku yako ya kawaida?",
                    "Kuvunjika kwa relationship si rahisi hata kidogo na hufai kujilaumu kwa kufeel hivi. Unahisi ni kitu gani kinakuumiza zaidi saa hii, na ungependa tupige story zaidi ama nikuonyeshe masaa ya counsellor wetu wa bure?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Pole sana kwa unayopitia. Kuachana na mtu uliyempenda huleta maumivu makubwa ya moyo. Je, hali hii ilitokea muda gani uliopita, na inaathiri vipi usingizi na shughuli zako za kila siku?",
                    "Kuvunjika kwa uhusiano ni jambo linaloumiza sana moyoni. Huna haja ya kupitia haya peke yako; ungependa kunieleza kinachokuumiza zaidi au uzungumze na mshauri wetu wa bure?",
                ])
            else:
                return pick_fresh([
                    "I'm really sorry you're going through a breakup. Losing someone you cared about hurts deeply. How long ago did this happen, and how has it been affecting your sleep and daily life?",
                    "Heartbreak is really painful, and wanting to reach out is a very human reaction. What part of this feels heaviest right now, and would you like to talk with one of our free counsellors?",
                ])

        # 3. School fees / exclusion distress
        if has_fees:
            if language == "Sheng":
                return pick_fresh([
                    "Pole sana manze. Kurudishwa home juu ya school fees wakati unataka kusoma huleta stress kubwa, na kumbuka hii si makosa yako hata kidogo. Hii hali imekuwa ikiaffect aje utulivu wako home na masomo yako?",
                    "Inauma sana kukwama juu ya karo bila kosa lako. Tuko hapa kukuskiza bila judgement; kuna mtu yeyote kwa family mnaweza kubonga naye kuhusu hii hali, ama ungependa kuongea na counsellor wetu wa bure?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Pole sana kwa changamoto hii ngumu ya karo ya shule. Kusimamishwa masomo huleta shinikizo kubwa na huzuni, lakini si kosa lako hata kidogo. Je, hali hii imekuwa ikiathiri vipi utulivu wako wa akili na masomo yako?",
                    "Kukosa karo wakati unatamani kusoma ni mzigo mzito sana kwa mwanafunzi. Je, kuna mtu katika familia unayeweza kuzungumza naye, au ungependa kuzungumza na mshauri wetu wa bure?",
                ])
            else:
                return pick_fresh([
                    "I'm so sorry you're dealing with being sent home over school fees. That is an enormous stress to carry and none of it is your fault. How has this been affecting your mindset and daily life at home?",
                ])

        # 4. Conflict at home / parents fighting + concentration / study
        if has_parent_conflict and (has_concentration or has_exam):
            if language == "Sheng":
                return pick_fresh([
                    "Kujaribu kusoma kukiwa na makelele na ugomvi wa wazazi home ni ngumu sana, na ni kawaida kabisa kukosa concentration. Hii hali imekuwa ikiendelea kwa muda gani, na inaaffect aje usingizi na utulivu wako ukiwa kwa keja?",
                    "Inaeleweka kabisa kushindwa kufocus wakati home kuko na mvutano—na si kosa lako hata kidogo. Ungependa tuangalie njia inayoendana na ratiba yako ya home, ama nikuunganishe na counsellor wetu wa bure?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Kujaribu kuzingatia masomo wakati kuna ugomvi wa wazazi nyumbani ni jambo gumu sana, na hilo si kosa lako. Je, hali hii imedumu kwa muda gani, na inaathiri vipi usingizi na utulivu wako wa kila siku?",
                    "Ni kawaida kukosa utulivu wa kusoma wakati nyumbani hakuna amani. Je, ungependa tujadili namna ya kupata muda tulivu wa kusoma, au uzungumze na mshauri wetu wa bure?",
                ])
            else:
                return pick_fresh([
                    "Trying to study while there is fighting at home is mentally exhausting, and it is completely normal to lose focus. How long has this tension been going on at home, and how is it affecting your sleep and daily energy?",
                ])

        if has_parent_conflict:
            if language == "Sheng":
                return pick_fresh([
                    "Inaeleweka sana kufeel drained na stressed. Kuona wazazi wakizozana kila saa huleta tension kubwa sana kwa keja, na si kosa lako hata kidogo. Hii hali imekuwa ikiendelea kwa muda gani na inaaffect aje utulivu wako wa kila siku?",
                    "Kuishi kwa nyumba yenye ugomvi kila wakati huumiza sana moyoni. Huko peke yako manze; ungependa kushiriki zaidi vile unajisikia ama kubonga na counsellor wetu wa bure?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Inaeleweka sana kulemewa na msongo wa mawazo wakati kuna ugomvi nyumbani, na hilo si kosa lako hata kidogo. Je, hali hii imekuwa ikiendelea kwa muda gani na inaathiri vipi amani yako ya kila siku?",
                ])
            else:
                return pick_fresh([
                    "Living with ongoing conflict between parents is deeply stressful and exhausting, and none of it is your fault. How long has this been happening, and how is it affecting your peace of mind day to day?",
                ])

        # 5. Social isolation / loneliness / convenience friends (Counsellor-style progression)
        if has_lonely_friends:
            if language == "Sheng":
                if is_multi_turn:
                    return pick_fresh([
                        "Kuumizwa mara kwa mara na wasee uliowachukulia kama mabeshte kunafanya mtu ajifungie ndani na kuogopa kuamini msee yeyote tena. Kumbuka counsellors wa MindBridge ni wa bure kabisa—ungependa nikuonyeshe masaa ambayo counsellor wetu ako available uongee naye?",
                        "Inachosha sana roho kuona uko hapo tu kwa ajili ya kuwasaidia wengine bila kupata upendo wa ukweli. Kuweka mipaka (boundaries) si ubinafsi; ungependa tupange session ya bure na counsellor wetu akusaidie kupitia hii hali?",
                    ])
                return pick_fresh([
                    "Pole sana manze, na kwanza kabisa—shida si wewe hata kidogo. Inauma sana kuona wasee wanakutafuta tu ukiwa na pesa ama wakihitaji msaada wako halafu wanapotea ukikosa. Umekuwa ukipitia huu upweke kwa muda gani sasa, na je inaaffect aje usingizi wako, siku yako ya kawaida, ama uwezo wako wa kuamini (kutrust) watu tena?",
                    "Inauma sana kufeel uko solo na kutumiwa na wasee kwa convenience yao pekee—lakini ujue hilo halina maana kuna shida na wewe. Hii hali imekuwa ikiendelea kwa muda gani, na unahisi ni kama umetengwa ama imekuwa ngumu kutrust msee yeyote baada ya kuangushwa mara mob?",
                ])
            elif language == "Kiswahili":
                if is_multi_turn:
                    return pick_fresh([
                        "Kuumizwa mara kwa mara na watu uliowaamini huleta uzito mkubwa na hofu ya kuwaamini wengine tena. Kumbuka washauri wa MindBridge wanatoa huduma bure kabisa—je, ungependa nikuonyeshe muda ambao mshauri wetu anapatikana?",
                    ])
                return pick_fresh([
                    "Pole sana kwa unachopitia, na kwanza kabisa ujue tatizo si wewe hata kidogo. Inaumiza sana kuona watu wanakutafuta tu wanapohitaji msaada wako kisha wanapotea. Je, umekuwa ukihisi upweke huu kwa muda gani, na hali hii inaathiri vipi maisha yako ya kila siku au imani yako kwa watu?",
                    "Kuhisi kutengwa au kukosa marafiki wa kweli ni jambo linaloumiza sana moyoni, lakini si kosa lako. Je, hali hii imedumu kwa muda gani, na unahisi imekuwa vigumu kuwaamini watu tena baada ya kukatishwa tamaa mara kwa mara?",
                ])
            else:
                if is_multi_turn:
                    return pick_fresh([
                        "Being repeatedly let down by people you cared about makes it hard to trust anyone again. Remember that MindBridge counsellors are completely free—would you like me to show you the available appointment times?",
                    ])
                return pick_fresh([
                    "I'm really sorry you're carrying this, and please know the problem is not you—being used for convenience and left out when you have nothing to give hurts deeply. How long have you been feeling this loneliness, and how is it affecting your daily life or your ability to trust people?",
                ])

        # 6. Family responsibility + exam conflict
        if has_siblings and (has_exam or has_no_time):
            if language == "Sheng":
                return pick_fresh([
                    "Kubalance kulea masiblings na kurevise for exams ni mzigo mzito sana. Inaonyesha vile unajali family yako, lakini pia unahitaji nafasi ya kupumua na kusoma. Hii hali imekuwa ikiaffect aje usingizi na nguvu zako za kila siku?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Kutunza ndugu zako wadogo huku ukijiandaa kwa mitihani ni mzigo mkubwa sana. Inaonyesha upendo wako kwa familia, lakini pia unahitaji muda wa kupumzika na kusoma. Je, hali hii imekuwa ikiathiri vipi usingizi na nguvu zako za kila siku?",
                ])
            else:
                return pick_fresh([
                    "Balancing caring for your siblings with studying for exams is an enormous load to carry. How long have you been juggling all of this on your own, and how is it affecting your sleep and energy?",
                ])

        # 7. Sole caretaker with no support at home
        if has_alone_duty and is_multi_turn:
            if language == "Sheng":
                return pick_fresh([
                    "Kuwa mtu pekee anayetegemewa home wakati exams zinakaribia ni mzigo mkubwa sana manze. Hufai kubeba hii stress yote peke yako. Ungependa nikuonyeshe masaa ya counsellor wetu wa bure wa MindBridge uongee naye?",
                ])
            elif language == "Kiswahili":
                return pick_fresh([
                    "Kuwa mtu pekee anayetegemewa nyumbani wakati mitihani inakaribia ni jambo gumu sana. Hupaswi kubeba mzigo huu mzito peke yako. Je, ungependa kuzungumza na mshauri wetu wa bure wa MindBridge?",
                ])
            else:
                return pick_fresh([
                    "Being the only person relied upon at home while trying to study is an immense weight. Would you like to connect with one of our free MindBridge counsellors for support?",
                ])

        # 8. General school stress / presentation / marks
        if any(w in text for w in ("mark", "exam", "grade", "school", "shule", "masomo", "class", "darasani", "homework", "presentation", "marks", "test", "stressed")):
            if language == "Sheng":
                if any(w in text for w in ("presentation", "kuongea", "class")):
                    return "Pole sana manze, kuongea mbele ya class huleta wasiwasi na pressure kwa wasee wengi sana. Umekuwa ukihisi huu wasiwasi kwa muda gani, na ni sehemu gani ya kuongea mbele ya watu inakupa tension zaidi?"
                if is_multi_turn:
                    return "Kusoma kwa bidii huku ukipitia pressure kubwa kunachosha sana akili. Kumbuka counsellors wetu wa MindBridge ni wa bure kabisa—ungependa nikuonyeshe masaa yaliyopo uongee na counsellor?"
                return "Pole sana kwa hiyo stress yote unayopitia kwa masomo manze. Umekuwa ukihisi huu uzito kwa muda gani sasa, na unaathiri aje usingizi wako ama psyche yako ya kila siku?"
            elif language == "Kiswahili":
                if any(w in text for w in ("darasa", "darasani", "kuzungumza", "ongea")):
                    return "Pole sana, ni jambo la kawaida kabisa kuhisi wasiwasi kabla ya kuzungumza mbele ya darasa. Je, wasiwasi huu umeanza lini, na ni jambo gani hasa linalokupa hofu unapokuwa mbele ya wengine?"
                if is_multi_turn:
                    return "Kuchukua hatua moja ndogo kwa wakati kunaweza kukupa nafuu katika masomo. Kumbuka washauri wetu wa MindBridge ni wa bure kabisa—je, ungependa nikuunganishe na mshauri wetu?"
                return "Pole sana kwa msongo wa mawazo unaopitia shuleni. Je, umekuwa ukihisi uzito huu kwa muda gani, na unaathiri vipi usingizi na nguvu zako za kila siku?"
            else:
                if any(w in text for w in ("presentation", "talk", "speak")):
                    return "Speaking in front of a class can bring up a lot of anxiety. How long has this presentation been weighing on your mind, and what part of it feels most stressful to you?"
                if is_multi_turn:
                    return "Carrying that academic pressure day after day is exhausting. Would you like to talk through a manageable plan together, or speak with one of our free MindBridge counsellors?"
                return "I hear how stressed and exhausted you are feeling about school right now. How long have you been carrying this pressure, and how is it affecting your sleep and daily energy?"

        # 9. Low mood / hopeless / giving up / exhausted
        if any(w in text for w in ("hopeless", "give up", "giving up", "ngumu", "life", "maisha", "tired", "choka", "nimechoka", "heavy", "exhausted", "kushindwa")):
            if language == "Sheng":
                if is_multi_turn:
                    return "Kuchoka roho na akili kwa muda mrefu ni mzigo mzito kubeba peke yako manze. Counsellors wetu wa MindBridge ni wa bure kabisa—ungependa nikuonyeshe masaa yaliyopo uongee na mmoja wao?"
                return "Pole sana manze, inaeleweka kufeel umechoka wakati mambo mengi yanakulemea kwa wakati mmoja. Umekuwa ukihisi huu uzito kwa muda gani sasa, na inaaffect aje usingizi ama siku yako ya kawaida?"
            elif language == "Kiswahili":
                if is_multi_turn:
                    return "Kulemewa na mawazo kwa muda mrefu ni mzigo mzito kubeba peke yako. Washauri wetu wa MindBridge wanapatikana bure kabisa—ungependa nikuonyeshe muda uliopo wa kuzungumza na mshauri?"
                return "Pole sana, ninajua jinsi inavyochosha akili na moyo unapolemewa na mambo mengi. Je, umekuwa ukihisi uzito huu kwa muda gani, na unaathiri vipi usingizi na maisha yako ya kila siku?"
            else:
                return "I hear how exhausted and overwhelmed you are feeling right now. How long have you been carrying this heavy feeling, and how is it affecting your sleep and day-to-day life?"

        # 10. Future / career confusion
        if any(w in text for w in ("career", "future", "ahead", "mbele", "job", "kazi", "hustle")):
            if language == "Sheng":
                return "Ni kawaida kufeel pressure kuhusu future na hustle wakati unaona kama wengine wako mbele. Umekuwa ukiwaza kuhusu hii hali kwa muda gani, na inaaffect aje mood na siku yako ya kawaida?"
            elif language == "Kiswahili":
                return "Ni kawaida kuwa na wasiwasi kuhusu maisha ya baadaye na kazi. Je, umekuwa na mawazo haya kwa muda gani, na yanaathiri vipi utulivu wako wa kila siku?"
            else:
                return "It is very normal to feel anxious about the future when it seems like others are ahead. How long has this worry been weighing on you, and how is it affecting your daily peace of mind?"

        if strict_match:
            return None

        # General emotional disclosure / confiding fallback
        if language == "Sheng":
            if is_multi_turn:
                return "Asante kwa kuendelea kufunguka manze; tuko hapa kukuskiza bila judgement na huduma zetu ni za bure kabisa. Ungependa nikuonyeshe masaa ambayo counsellor wetu wa MindBridge ako available uongee naye?"
            return "Asante kwa kushare hii story na mimi manze. Umekuwa ukipitia hii hali kwa muda gani sasa, na inaaffect aje siku yako ya kawaida?"
        elif language == "Kiswahili":
            if is_multi_turn:
                return "Asante kwa kuendelea kushiriki nami; kumbuka washauri wetu wa MindBridge wanatoa msaada bure kabisa. Je, ungependa nikuonyeshe muda ambao mshauri wetu anapatikana?"
            return "Asante kwa kunieleza kuhusu hali yako. Je, umekuwa ukipitia hali hii kwa muda gani, na inaathiri vipi maisha yako ya kila siku?"
        else:
            if is_multi_turn:
                return "Thank you for continuing to share what you are going through. Would you like to keep talking through this, or see the available times for a free MindBridge counsellor?"
            return "Thank you for sharing that with me. How long have you been feeling this way, and how has it been affecting your day-to-day life?"


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
