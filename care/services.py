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
WELCOME = ("Sema. How are you feeling? Reply na number — 1 ni very low, 5 ni poa kabisa. "
           "You can also ask for a counsellor at any time.")
AFTER_MOOD = ("Thank you for checking in. If you'd like to share more, just write a message. "
              "You can also ask for a counsellor or check in again whenever you want.")
SUPPORT = ("Thanks for reaching out. A counsellor will review your message. "
           "If you are in immediate danger, contact a trusted adult or call Kenya emergency services on 999 or 112 now.")


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
    if incoming.participant.is_simulated:
        return None
    return OutboundMessage.objects.get_or_create(
        dedupe_key=f"reply:{incoming.external_id}", defaults={"participant": incoming.participant,
        "inbound": incoming, "payload": text_payload(incoming.participant.wa_id, incoming.reply, buttons)})[0]


def template_payload(wa_id, name, language="en"):
    return {"to": wa_id, "type": "template", "template": {
        "namespace": settings.TURN_TEMPLATE_NAMESPACE, "name": name,
        "language": {"code": language, "policy": "deterministic"}, "components": []}}


def queue_template(participant, name, key):
    if not (not participant.is_simulated and participant.consented and participant.wa_id and name and settings.TURN_TEMPLATE_NAMESPACE):
        return None
    return OutboundMessage.objects.get_or_create(dedupe_key=key, defaults={
        "participant": participant, "payload": template_payload(participant.wa_id, name,
                                                                   settings.TURN_TEMPLATE_LANGUAGE)})[0]


def queue_session_confirmation(session):
    person = session.participant
    if person.is_simulated or not person.consented or not person.wa_id:
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
            if item.participant.is_simulated or (not item.inbound_id and not item.participant.consented):
                item.status = "cancelled"
                item.save(update_fields=["status"])
                continue
            if item.recipient_counsellor_id:
                from .models import CounsellorProfile
                profile = CounsellorProfile.objects.filter(user_id=item.recipient_counsellor_id,
                    user__is_active=True, notification_opt_in=True).first()
                if not profile or profile.whatsapp_number != item.payload.get("to"):
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
    for person in Participant.objects.filter(consented=True, onboarding_complete=True, is_simulated=False, deletion_requested_at__isnull=True, wa_id__isnull=False):
        # Older opted-in rows have no consent timestamp; do not invent missed history.
        start = timezone.localtime(person.consented_at).date() if person.consented_at else week
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
        if (len(closed) >= 2 and all(c.status == "missed" for c in closed[:2]) and
            not person.inbound_messages.filter(received_at__date__gte=closed[1].week_start,
                received_at__date__lt=week).exists()):
            reason = "Two missed weekly check-ins"
            if not person.alerts.filter(reason=reason, status=RiskAlert.OPEN).exists():
                from .workflows import create_alert
                create_alert(person, "medium", reason, "weekly schedule")
        # An approved template permits an outbound prompt outside the 24-hour service window.
        if today == week and not person.moods.filter(recorded_at__date__gte=week).exists():
            queue_template(person, settings.TURN_CHECKIN_TEMPLATE_NAME, f"weekly:{person.pk}:{week}")
    return created, missed



def risk_signals(participant, text=""):
    from .risk import assess
    return assess(participant, text)


def process_message(participant, body, external_id):
    """Persistent conversation used by Turn.io and by the staff-only local test chat."""
    from .workflows import assign_counsellor, create_alert, slot_prompt, select_booking
    from .risk import assess
    with transaction.atomic():
        participant = Participant.objects.select_for_update().get(pk=participant.pk)
        existing = InboundMessage.objects.filter(external_id=external_id).first()
        if existing:
            return existing, False
        text = body.strip()[:4000]
        incoming = InboundMessage.objects.create(external_id=external_id, participant=participant, body=text)
        command = text.casefold()
        command = {"consent_yes": "i agree", "consent_no": "not now", "request_session": "session",
                   "checkin": "check in", "pause": "pause", "minor_yes": "i understand"}.get(command, command)
        participant.last_inbound_at = timezone.now()
        buttons = ()
        classification = None
        analyse = False
        if command in ("delete my data", "delete data"):
            participant.deletion_requested_at = participant.deletion_requested_at or timezone.now()
            participant.consented = False
            OutboundMessage.objects.filter(participant=participant, status="pending").update(status="cancelled")
            reply = "Your deletion request is recorded. Check-ins are paused; your profile and linked records will be deleted within 30 days."
        elif participant.deletion_requested_at:
            reply = "Your deletion request is pending. Check-ins are paused."
        elif command in ("privacy", "my data"):
            reply = ("We store your nickname, age, WhatsApp ID, check-ins and appointments for assigned care staff. "
                     "Mood and message records are kept for at most 12 months. Type Delete my data to request deletion within 30 days, or Pause to stop check-ins.")
        elif command in ("stop", "pause", "pause check-ins", "not now"):
            participant.consented = False
            participant.consented_at = None
            participant.flow_state = "menu"
            reply = "That's okay. Check-ins are paused. Message us whenever you're ready to continue."
            OutboundMessage.objects.filter(participant=participant, status="pending").update(status="cancelled")
            buttons = (("consent_yes", "I agree"),)
        elif not participant.consented:
            if command in ("i agree", "yes, i agree"):
                participant.consented = True
                participant.consented_at = timezone.now()
                if participant.onboarding_complete:
                    assign_counsellor(participant)
                    participant.flow_state = "mood"
                    reply = WELCOME
                else:
                    participant.flow_state = "nickname"
                    reply = "Karibu. What nickname would you like us to use? You don't need to share your real name."
            else:
                reply = CONSENT
                buttons = (("consent_yes", "I agree"), ("consent_no", "Not now"))
        elif not participant.onboarding_complete:
            if participant.flow_state == "nickname":
                if not 2 <= len(text) <= 80:
                    reply = "Please choose a nickname between 2 and 80 characters."
                else:
                    participant.display_name = text
                    participant.flow_state = "age"
                    reply = "How old are you? Send your age as a number. This prototype is for ages 13–24."
            elif participant.flow_state == "age":
                if not command.isdigit() or not 13 <= int(command) <= 24:
                    reply = "This prototype is for ages 13–24. Please enter an age in that range, or choose Not now."
                else:
                    participant.age = int(command)
                    if participant.age < 18:
                        participant.flow_state = "minor_consent"
                        reply = ("Before we continue: your check-ins will be saved for your assigned counsellor. "
                                 "You can pause or ask us to delete them. MindBridge isn't an emergency service. "
                                 "Do you understand and want to continue? This records your agreement, not guardian permission.")
                        buttons = (("minor_yes", "I understand"), ("consent_no", "Not now"))
                    else:
                        participant.onboarding_complete = True
                        assign_counsellor(participant)
                        participant.flow_state = "mood"
                        reply = WELCOME
            elif participant.flow_state == "minor_consent":
                if command in ("i understand", "i agree"):
                    participant.minor_assent_at = timezone.now()
                    participant.onboarding_complete = True
                    assign_counsellor(participant)
                    participant.flow_state = "mood"
                    reply = WELCOME
                else:
                    reply = "Choose I understand to continue, or Not now to pause."
                    buttons = (("minor_yes", "I understand"), ("consent_no", "Not now"))
            else:
                participant.flow_state = "nickname"
                reply = "Let's finish your profile. What nickname should we use?"
        elif command in ("counsellor", "talk to a counsellor", "talk to counsellor", "session"):
            reply = slot_prompt(participant)
            buttons = (("checkin", "Check in"), ("pause", "Pause"))
        elif command in ("check in", "check in again", "check-in", "mood"):
            participant.flow_state = "mood"
            reply = WELCOME
        elif participant.flow_state == "booking":
            reply = select_booking(participant, command)
            buttons = (("checkin", "Check in"), ("request_session", "Counsellor"))
        elif participant.flow_state == "mood" and command in ("1", "2", "3", "4", "5"):
            MoodEntry.objects.create(participant=participant, score=int(command), recorded_at=timezone.now())
            participant.flow_state = "note"
            reply = AFTER_MOOD
            analyse = True
            buttons = (("request_session", "Counsellor"), ("checkin", "Check in again"))
        else:
            # Free text remains conversational beyond the first note.
            latest = participant.moods.order_by("-recorded_at").first()
            classification = classify_note(text)
            if participant.flow_state == "note" and latest:
                latest.note = text
                latest.sentiment_label = ""
                latest.sentiment_score = None
                latest.sentiment_source = ""
                latest.sentiment_risk_eligible = False
                if classification:
                    latest.sentiment_label = classification.label
                    latest.sentiment_score = classification.confidence
                    latest.sentiment_source = classification.source
                    latest.sentiment_risk_eligible = classification.risk_eligible
                latest.save(update_fields=["note", "sentiment_label", "sentiment_score",
                                          "sentiment_source", "sentiment_risk_eligible"])
            participant.flow_state = "menu"
            analyse = True
            history = list(participant.inbound_messages.order_by("-received_at").values("body", "reply")[:6])
            reply = generate_response(text, {"participant_id": participant.pk, "history": list(reversed(history))}) or (
                "Asante for sharing. Your counsellor can review your message. You can keep writing, check in, or ask for a session.")
            buttons = (("request_session", "Counsellor"), ("checkin", "Check in again"))
        participant.save()
        if (participant.consented and participant.onboarding_complete and not analyse
            and command not in ("i agree", "yes, i agree", "i understand", "privacy", "my data", "counsellor",
                "talk to a counsellor", "talk to counsellor", "session", "check in", "check in again", "check-in", "mood")
            and not command.isdigit()):
            analyse = True  # Include free text sent while choosing an appointment.
        signal = assess(participant, text, classification) if analyse else None
        if classification:
            incoming.sentiment_label = classification.label
            incoming.sentiment_score = classification.confidence
            incoming.sentiment_source = classification.source
            incoming.sentiment_risk_eligible = classification.risk_eligible
        if signal:
            priority, reason, source = signal
            create_alert(participant, priority, reason, source)
            if priority == "high":
                reply = SUPPORT
                buttons = (("request_session", "Counsellor"),)
        incoming.reply = reply
        incoming.save(update_fields=["reply", "sentiment_label", "sentiment_score",
                                     "sentiment_source", "sentiment_risk_eligible"])
        incoming.suggested_buttons = buttons
        queue_reply(incoming, buttons)
        return incoming, True
