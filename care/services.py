"""Small, testable interfaces between WhatsApp and the care database."""
import base64
import hmac
import json
import re
from hashlib import sha256
from urllib.request import Request, urlopen
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import InboundMessage, Keyword, MoodEntry, Participant, RiskAlert, SessionRequest

WELCOME = ("Welcome to MindBridge. Reply 1 for a mood check-in, 2 to request a counsellor "
           "session, or HELP to see these options again. You can reply STOP to pause check-ins.")
SUPPORT = ("Thanks for reaching out. A counsellor will review your message. "
           "If you need immediate help, contact a trusted adult or local emergency service now.")


def valid_turn_signature(body, signature):
    secret = settings.TURN_WEBHOOK_SECRET
    if not secret or not signature:
        return False
    expected = base64.b64encode(hmac.new(secret.encode(), body, sha256).digest()).decode()
    return hmac.compare_digest(expected, signature.strip())


def send_turn_text(wa_id, text):
    """True only after Turn accepts the message; never send without a token."""
    if not settings.TURN_API_TOKEN:
        return False
    payload = json.dumps({"to": wa_id, "type": "text", "text": {"body": text}}).encode()
    req = Request("https://whatsapp.turn.io/v1/messages", data=payload, headers={
        "Authorization": f"Bearer {settings.TURN_API_TOKEN}", "Content-Type": "application/json",
    }, method="POST")
    with urlopen(req, timeout=8) as response:
        return 200 <= response.status < 300


def risk_signals(participant, text=""):
    """Rules and configured terms. The optional classifier can be added later."""
    scores = list(participant.moods.order_by("-recorded_at").values_list("score", flat=True)[:3])
    mood = len(scores) == 3 and all(score <= 2 for score in scores)
    sudden_drop = len(scores) >= 2 and scores[1] - scores[0] >= 3
    matches = [k for k in Keyword.objects.filter(is_active=True) if
               set(re.findall(r"\w+", k.term.casefold())) and
               re.search(r"(?<!\w)" + re.escape(k.term.casefold()) + r"(?!\w)", text.casefold())]
    override = any(k.tier == 1 for k in matches)
    # A single behavioural signal stays visible as a medium-priority alert for human review.
    # No model confidence is invented while the classifier is being trained.
    if override:
        return "high", "Urgent keyword review", "configured keyword"
    if mood or sudden_drop:
        return "medium", "Mood pattern review", "mood rule"
    if matches:
        return "medium", "Keyword review", "configured keyword"
    return None


def process_message(participant, body, external_id):
    """Idempotent scripted flow; response is saved for retry after send failure."""
    with transaction.atomic():
        existing = InboundMessage.objects.select_for_update().filter(external_id=external_id).first()
        if existing:
            return existing, False
        text = body.strip()[:4000]
        incoming = InboundMessage.objects.create(external_id=external_id, participant=participant, body=text)
        command = text.casefold()
        if command == "stop":
            participant.consented = False
            participant.flow_state = "menu"
            reply = "Check-ins paused. Reply START if you want to use MindBridge again."
        elif not participant.consented:
            if command == "start":
                participant.consented = True
                reply = WELCOME
            else:
                reply = "Reply START to use MindBridge. Your check-ins will begin only after you opt in."
        elif command in ("help", "menu", "hi", "hello"):
            participant.flow_state = "menu"
            reply = WELCOME
        elif participant.flow_state == "mood" and command in ("1", "2", "3", "4", "5"):
            MoodEntry.objects.create(participant=participant, score=int(command), recorded_at=timezone.now())
            participant.flow_state = "note"
            reply = "Thank you for checking in. You can share a short note, or reply SKIP."
        elif participant.flow_state == "note":
            participant.flow_state = "menu"
            note = "" if command == "skip" else text
            latest = participant.moods.order_by("-recorded_at").first()
            if latest:
                latest.note = note
                latest.save(update_fields=["note"])
            reply = "Thank you. Your check-in is saved. Reply HELP for options."
        elif command in ("1", "mood"):
            participant.flow_state = "mood"
            reply = "How are you feeling today? Reply with a number from 1 (very low) to 5 (very good)."
        elif command in ("2", "session"):
            SessionRequest.objects.create(participant=participant)
            participant.flow_state = "menu"
            reply = "Your session request has been recorded. A counsellor will follow up. Reply HELP for options."
        else:
            reply = WELCOME
        participant.save(update_fields=["consented", "flow_state"])
        signal = risk_signals(participant, text) if participant.consented else None
        if signal:
            priority, reason, source = signal
            recent = RiskAlert.objects.filter(participant=participant, reason=reason,
                status=RiskAlert.OPEN, created_at__gte=timezone.now() - timezone.timedelta(days=1)).exists()
            if not recent:
                RiskAlert.objects.create(participant=participant, priority=priority,
                                         reason=reason, trigger_source=source)
            if priority == "high":
                reply = SUPPORT
        incoming.reply = reply
        incoming.save(update_fields=["reply"])
        return incoming, True
