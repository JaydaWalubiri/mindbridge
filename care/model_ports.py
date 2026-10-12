"""Local sentiment inference and the separate conversation-model boundary."""
from dataclasses import dataclass
from functools import lru_cache
import logging
import math
import threading
import json
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from django.conf import settings
from .response_policy import language_name, rejection_reason, route, scripted_reply

logger = logging.getLogger(__name__)
_load_lock = threading.Lock()


@dataclass(frozen=True)
class Classification:
    label: str
    confidence: float
    source: str = ""
    risk_eligible: bool = True


class ReplyText(str):
    """Keep the string boundary while recording reply provenance."""
    def __new__(cls, text, source):
        value = super().__new__(cls, text)
        value.source = source
        return value


@lru_cache(maxsize=2)
def _load_model(model_id, revision, download=False):
    """Cache failures until restart; never download inside a chat request."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        options = dict(revision=revision, local_files_only=not download, trust_remote_code=False)
        tokenizer = AutoTokenizer.from_pretrained(model_id, **options)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_id, use_safetensors=True, **options)
        labels = {str(label).casefold() for label in model.config.id2label.values()}
        if not labels or not labels.issubset({"negative", "neutral", "positive"}):
            raise ValueError("Model must provide named sentiment labels")
        model.eval()
        return tokenizer, model
    except Exception as error:
        # Do not log message text or exception details that may contain input.
        logger.warning("Sentiment model unavailable (%s); rules remain active.", type(error).__name__)
        return None


def classify_note(text: str) -> Classification | None:
    if not settings.SENTIMENT_ENABLED or not text.strip():
        return None
    with _load_lock:
        assets = _load_model(settings.SENTIMENT_MODEL, settings.SENTIMENT_REVISION)
    if assets is None:
        return None
    try:
        import torch
        tokenizer, model = assets
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.inference_mode():
            scores = model(**inputs).logits[0].softmax(dim=-1)
        index = int(scores.argmax().item())
        label = model.config.id2label[index].casefold()
        score = float(scores[index].item())
        if label not in {"negative", "neutral", "positive"} or not math.isfinite(score) or not 0 <= score <= 1:
            return None
        return Classification(label, score,
            f"{settings.SENTIMENT_MODEL}@{settings.SENTIMENT_REVISION}", settings.SENTIMENT_RISK_ENABLED)
    except Exception as error:
        logger.warning("Sentiment inference failed (%s); rules remain active.", type(error).__name__)
        return None


def generate_response(text: str, context: dict) -> str | None:
    language = language_name(context.get("language", "en"))
    kind = route(text)
    if kind:
        return ReplyText(scripted_reply(kind, language), "scripted_" + kind)
    if not settings.CONVERSATION_ENABLED:
        return None
    fallback = ReplyText(scripted_reply("fallback", language), "scripted_fallback")
    parsed = urlsplit(settings.CONVERSATION_URL)
    local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if (not parsed.hostname or parsed.username or parsed.password or parsed.fragment
            or parsed.query or not settings.CONVERSATION_API_TOKEN
            or not (parsed.scheme == "https" or
                    (settings.DEBUG and parsed.scheme == "http" and local))):
        logger.warning("Conversation endpoint is not safely configured; using scripted support.")
        return fallback
    history = []
    # Only completed earlier exchanges; do not duplicate the current user turn.
    for item in context.get("history", [])[-6:]:
        if isinstance(item, dict) and item.get("body") and item.get("reply"):
            history.extend([{"role": "user", "content": str(item["body"])[:4000]},
                            {"role": "assistant", "content": str(item["reply"])[:1400]}])
    payload = json.dumps({"message": text[:4000], "language": language,
                          "history": history}, ensure_ascii=False).encode("utf-8")
    request = Request(settings.CONVERSATION_URL, data=payload, method="POST", headers={
        "Authorization": "Bearer " + settings.CONVERSATION_API_TOKEN,
        "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with build_opener(_NoRedirect()).open(request, timeout=settings.CONVERSATION_TIMEOUT) as response:
            raw = response.read(16385)
        if len(raw) > 16384:
            return fallback
        result = json.loads(raw)
        if not isinstance(result, dict) or result.get("language") != language:
            return fallback
        source = result.get("model_source")
        expected = settings.CONVERSATION_EXPECTED_SOURCE
        if not expected or source not in {expected, "scripted_fallback", "scripted_safeguard"}:
            return fallback
        reply = result.get("reply")
        if rejection_reason(reply, language, result.get("token_limit_reached", False)):
            return fallback
        return ReplyText(reply.strip(), source)
    except (OSError, ValueError, TypeError):
        # Never include participant text, endpoint secrets or provider error bodies.
        logger.warning("Conversation request failed; using scripted support.")
        return fallback


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
