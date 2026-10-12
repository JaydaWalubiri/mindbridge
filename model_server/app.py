"""Authenticated, bounded inference endpoint for supervised prototype testing."""
from contextlib import asynccontextmanager
import hmac
import json
import os
from pathlib import Path
import threading
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, model_validator

from care.response_policy import (rejection_reason, route, scripted_reply)

ROOT = Path(__file__).resolve().parent


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
        self.model = PeftModel.from_pretrained(base, manifest["adapter_repo"],
            revision=manifest["adapter_revision"], is_trainable=False, **options)
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
        # Time-limited or token-limited partial generations are never sent as replies.
        complete = int(generated[-1]) == tokenizer.eos_token_id if len(generated) else False
        return {"raw_response": tokenizer.decode(generated, skip_special_tokens=True),
                "token_limit_reached": not complete}


def create_app(engine=None, token=None):
    supplied = engine
    service_token = token if token is not None else os.environ.get("MODEL_SERVICE_TOKEN", "")
    bearer = HTTPBearer(auto_error=False)
    lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(app):
        if len(service_token) < 32:
            raise RuntimeError("Set a separate MODEL_SERVICE_TOKEN of at least 32 characters")
        app.state.engine = supplied if supplied is not None else GPUModel()
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
