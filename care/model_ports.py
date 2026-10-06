"""Local sentiment inference and the separate conversation-model boundary."""
from dataclasses import dataclass
from functools import lru_cache
import logging
import math
import threading
from django.conf import settings

logger = logging.getLogger(__name__)
_load_lock = threading.Lock()


@dataclass(frozen=True)
class Classification:
    label: str
    confidence: float
    source: str = ""
    risk_eligible: bool = True


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
    return None
