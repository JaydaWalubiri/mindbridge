"""Small, testable interfaces between WhatsApp and the care database."""
import base64
import hmac
import json
import re
from hashlib import sha256
from urllib.request import Request, urlopen
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .models import InboundMessage, Keyword, MoodEntry, OutboundMessage, Participant, RiskAlert, SessionRequest, WeeklyCheckIn
from .model_ports import classify_note, generate_response

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


def send_turn_payload(payload):
    """Return Turn's accepted message ID; raise on a failed HTTP request."""
    if not settings.TURN_API_TOKEN:
        raise RuntimeError("TURN_API_TOKEN is not configured")
    payload = json.dumps(payload).encode()
    req = Request("https://whatsapp.turn.io/v1/messages", data=payload, headers={
        "Authorization": f"Bearer {settings.TURN_API_TOKEN}", "Content-Type": "application/json",
    }, method="POST")
    with urlopen(req, timeout=8) as response:
        result = json.load(response)
        return result.get("messages", [{}])[0].get("id", "")


def text_payload(wa_id, body, buttons=()):
    if buttons:
        return {"to": wa_id, "type": "interactive", "interactive": {
            "type": "button", "body": {"text": body}, "action": {"buttons": [
                {"type": "reply", "reply": {"id": key, "title": title}}
                for key, title in buttons[:3]]}}}
    return {"to": wa_id, "type": "text", "text": {"body": body}}


def queue_reply(incoming, buttons=()):
    return OutboundMessage.objects.get_or_create(
        dedupe_key=f"reply:{incoming.external_id}", defaults={"participant": incoming.participant,
        "inbound": incoming, "payload": text_payload(incoming.participant.wa_id, incoming.reply, buttons)})[0]


def template_payload(wa_id, name, language="en"):
    return {"to": wa_id, "type": "template", "template": {
        "namespace": settings.TURN_TEMPLATE_NAMESPACE, "name": name,
        "language": {"code": language, "policy": "deterministic"}, "components": []}}


def queue_template(participant, name, key):
    if not (participant.consented and participant.wa_id and name and settings.TURN_TEMPLATE_NAMESPACE):
        return None
    return OutboundMessage.objects.get_or_create(dedupe_key=key, defaults={
        "participant": participant, "payload": template_payload(participant.wa_id, name,
                                                                   settings.TURN_TEMPLATE_LANGUAGE)})[0]


def queue_session_confirmation(session):
    person = session.participant
    if not person.consented or not person.wa_id:
        return None
    when = timezone.localtime(session.starts_at).strftime("%d %b %Y at %H:%M")
    key = f"session:{session.pk}"
    if person.last_inbound_at and person.last_inbound_at >= timezone.now() - timedelta(hours=23):
        payload = text_payload(person.wa_id, f"Your MindBridge session is scheduled for {when}. "
                               "Reply here if you need to change it.")
    elif settings.TURN_SESSION_TEMPLATE_NAME and settings.TURN_TEMPLATE_NAMESPACE:
        payload = template_payload(person.wa_id, settings.TURN_SESSION_TEMPLATE_NAME,
                                   settings.TURN_TEMPLATE_LANGUAGE)
        payload["template"]["components"] = [{"type": "body", "parameters": [
            {"type": "text", "text": when}]}]
    else:
        return None
    return OutboundMessage.objects.get_or_create(dedupe_key=key, defaults={
        "participant": person, "payload": payload})[0]


def deliver_due(limit=50):
    """Run from a separate worker, never from the inbound webhook request."""
    count = 0
    due = list(OutboundMessage.objects.filter(status="pending", next_attempt_at__lte=timezone.now())
               .values_list("pk", flat=True)[:limit])
    for pk in due:
        with transaction.atomic():
            item = OutboundMessage.objects.select_for_update().select_related("participant", "inbound").get(pk=pk)
            if item.status != "pending" or item.next_attempt_at > timezone.now():
                continue
            # Consent may be withdrawn after a weekly reminder was queued.
            if not item.inbound_id and not item.participant.consented:
                item.status = "cancelled"
                item.save(update_fields=["status"])
                continue
            if not settings.TURN_API_TOKEN:
                continue
            try:
                provider_id = send_turn_payload(item.payload)
                if not provider_id:
                    raise ValueError("Turn did not return a message ID")
            except (OSError, ValueError, RuntimeError) as error:
                item.attempts += 1
                item.last_error = type(error).__name__ + ": " + str(error)[:190]
                item.status = "failed" if item.attempts >= 5 else "pending"
                item.next_attempt_at = timezone.now() + timedelta(minutes=min(60, 2 ** item.attempts))
                item.save(update_fields=["attempts", "last_error", "status", "next_attempt_at"])
                continue
            item.status = "sent"
            item.sent_at = timezone.now()
            item.provider_message_id = provider_id
            item.attempts += 1
            item.save(update_fields=["status", "sent_at", "provider_message_id", "attempts"])
            if item.inbound_id:
                InboundMessage.objects.filter(pk=item.inbound_id).update(delivered=True)
            count += 1
    return count


def run_weekly_checkins(today=None):
    """Idempotent weekly cycle; called daily in the configured Nairobi timezone."""
    today = today or timezone.localdate()
    week = today - timedelta(days=today.weekday())
    created = missed = 0
    for person in Participant.objects.filter(consented=True, wa_id__isnull=False):
        start = max(person.consented_at.date() if person.consented_at else person.created_at.date(),
                    person.created_at.date())
        first_week = start - timedelta(days=start.weekday())
        current = first_week
        while current <= week:
            cycle, new = WeeklyCheckIn.objects.get_or_create(participant=person, week_start=current)
            created += int(new)
            # Evaluate completed weeks, and reflect an early response in the current week.
            has_mood = person.moods.filter(recorded_at__date__gte=current,
                                           recorded_at__date__lt=current + timedelta(days=7)).exists()
            state = "completed" if has_mood else ("missed" if current < week else "pending")
            if cycle.status != state:
                cycle.status = state
                cycle.save(update_fields=["status"])
                missed += int(state == "missed")
            current += timedelta(days=7)
        weeks = list(person.weekly_checkins.order_by("-week_start")[:3])
        closed = [c for c in weeks if c.week_start < week]
        if len(closed) >= 2 and all(c.status == "missed" for c in closed[:2]):
            reason = "Two missed weekly check-ins"
            if not person.alerts.filter(reason=reason, status=RiskAlert.OPEN).exists():
                RiskAlert.objects.create(participant=person, priority="medium", reason=reason,
                                         trigger_source="weekly schedule")
        # An approved template permits an outbound prompt outside the 24-hour service window.
        if today == week and not person.moods.filter(recorded_at__date__gte=week).exists():
            queue_template(person, settings.TURN_CHECKIN_TEMPLATE_NAME, f"weekly:{person.pk}:{week}")
    return created, missed


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
    """Idempotent scripted flow; responses enter the durable outbound queue."""
    with transaction.atomic():
        existing = InboundMessage.objects.select_for_update().filter(external_id=external_id).first()
        if existing:
            return existing, False
        text = body.strip()[:4000]
        incoming = InboundMessage.objects.create(external_id=external_id, participant=participant, body=text)
        command = text.casefold()
        command = {"consent_yes": "i agree", "consent_no": "not now",
                   "request_session": "session", "checkin": "check in", "pause": "pause"}.get(command, command)
        participant.last_inbound_at = timezone.now()
        buttons = ()
        if command in ("stop", "pause", "pause check-ins", "not now"):
            participant.consented = False
            participant.consented_at = None
            participant.flow_state = "menu"
            reply = "That's okay. Check-ins are paused. Message us whenever you're ready to continue."
        elif not participant.consented:
            if command in ("i agree", "yes, i agree"):
                participant.consented = True
                participant.consented_at = timezone.now()
                participant.flow_state = "mood"
                reply = WELCOME
            else:
                reply = CONSENT
                buttons = (("consent_yes", "I agree"), ("consent_no", "Not now"))
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
            buttons = (("request_session", "Counsellor"), ("checkin", "Check in again"))
        elif participant.flow_state == "note":
            participant.flow_state = "menu"
            latest = participant.moods.order_by("-recorded_at").first()
            if latest:
                latest.note = text
                classification = classify_note(text)
                if classification:
                    latest.sentiment_label = classification.label
                    latest.sentiment_score = classification.confidence
                latest.save(update_fields=["note", "sentiment_label", "sentiment_score"])
            reply = generate_response(text, {"participant_id": participant.pk}) or (
                "Thank you for sharing. A counsellor can review your note. "
                "You can check in again or ask for a counsellor.")
            buttons = (("request_session", "Counsellor"), ("checkin", "Check in again"))
        else:
            reply = "You can check in about your mood or ask for a counsellor. Tell us which you'd like."
            buttons = (("checkin", "Check in"), ("request_session", "Counsellor"), ("pause", "Pause"))
        participant.save(update_fields=["consented", "consented_at", "flow_state", "last_inbound_at"])
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
                buttons = ()
        incoming.reply = reply
        incoming.save(update_fields=["reply"])
        queue_reply(incoming, buttons)
        return incoming, True
