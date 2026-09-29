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

CONSENT = ("Welcome to MindBridge. We can save your check-ins so a counsellor can review them. "
           "Is that okay? Reply 'I agree' to continue, or 'not now'.")
WELCOME = ("How are you feeling today? Send a number from 1 (very low) to 5 (very good). "
           "You can also ask for a counsellor at any time.")
AFTER_MOOD = ("Thank you for checking in. If you'd like to share more, just write a message. "
              "You can also ask for a counsellor or check in again whenever you want.")
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
        if command in ("stop", "pause", "pause check-ins", "not now"):
            participant.consented = False
            participant.flow_state = "menu"
            reply = "That's okay. Check-ins are paused. Message us whenever you're ready to continue."
        elif not participant.consented:
            if command in ("i agree", "yes, i agree"):
                participant.consented = True
                participant.flow_state = "mood"
                reply = WELCOME
            else:
                reply = CONSENT
        elif command in ("counsellor", "talk to a counsellor", "talk to counsellor", "session"):
            SessionRequest.objects.create(participant=participant)
            participant.flow_state = "menu"
            reply = "Your request has been recorded. A counsellor will follow up. You can write to us again whenever you need to."
        elif command in ("check in", "check in again", "check-in", "mood"):
            participant.flow_state = "mood"
            reply = WELCOME
        elif participant.flow_state == "mood" and command in ("1", "2", "3", "4", "5"):
            MoodEntry.objects.create(participant=participant, score=int(command), recorded_at=timezone.now())
            participant.flow_state = "note"
            reply = AFTER_MOOD
        elif participant.flow_state == "note":
            participant.flow_state = "menu"
            latest = participant.moods.order_by("-recorded_at").first()
            if latest:
                latest.note = text
                latest.save(update_fields=["note"])
            reply = "Thank you for sharing. A counsellor can review your note. You can check in again or ask for a counsellor."
        else:
            reply = "You can check in about your mood or ask for a counsellor. Tell us which you'd like."
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
