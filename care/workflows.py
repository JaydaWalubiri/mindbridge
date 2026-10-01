"""Proposal workflows shared by the Turn webhook and the restricted local simulator."""
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import (AssignmentRotation, AvailabilitySlot, CounsellorProfile, InboundMessage,
                     MoodEntry, OutboundMessage, Participant, RiskAlert, Session, SessionRequest)


def assign_counsellor(person):
    if person.counsellor_id:
        return person.counsellor
    with transaction.atomic():
        cursor = AssignmentRotation.objects.select_for_update().get(pk=1)
        profiles = list(CounsellorProfile.objects.filter(accepts_assignments=True,
                         user__is_active=True).select_related("user").order_by("user_id"))
        if not profiles:
            return None
        selected = next((p for p in profiles if p.user_id > cursor.last_user_id), profiles[0])
        cursor.last_user_id = selected.user_id
        cursor.save(update_fields=["last_user_id"])
        person.counsellor = selected.user
        person.save(update_fields=["counsellor"])
        return selected.user


def queue_staff_notice(person, user, message, key):
    from .services import template_payload
    if person.is_simulated or not user or not person.consented:
        return None
    profile = CounsellorProfile.objects.filter(user=user, notification_opt_in=True).first()
    if not (profile and profile.whatsapp_number and settings.TURN_STAFF_TEMPLATE_NAME
            and settings.TURN_TEMPLATE_NAMESPACE):
        return None
    payload = template_payload(profile.whatsapp_number, settings.TURN_STAFF_TEMPLATE_NAME,
                               settings.TURN_TEMPLATE_LANGUAGE)
    payload["template"]["components"] = [{"type": "body", "parameters": [{"type": "text", "text": message}]}]
    return OutboundMessage.objects.get_or_create(dedupe_key=key, defaults={
        "participant": person, "recipient_counsellor": user, "payload": payload})[0]


def create_alert(person, priority, reason, source):
    existing = person.alerts.filter(status="open", reason=reason,
                                    created_at__gte=timezone.now()-timedelta(days=1)).first()
    if existing:
        return existing
    alert = RiskAlert.objects.create(participant=person, priority=priority, reason=reason, trigger_source=source)
    queue_staff_notice(person, person.counsellor,
                       f"MindBridge: review {person.code} ({priority} priority) in your dashboard.", f"alert:{alert.pk}")
    return alert


def available_slots(person):
    if not person.counsellor_id:
        return []
    candidates = AvailabilitySlot.objects.filter(counsellor=person.counsellor,
        starts_at__gt=timezone.now(), is_active=True, session__isnull=True).order_by("starts_at")
    return [slot for slot in candidates if not overlapping(person.counsellor, slot.starts_at)][:5]


def overlapping(user, starts_at, exclude_session=None):
    # All appointments and advertised slots are 30 minutes, in EAT in the UI.
    query = Session.objects.filter(counsellor=user, status="scheduled",
        starts_at__gt=starts_at-timedelta(minutes=30), starts_at__lt=starts_at+timedelta(minutes=30))
    if exclude_session:
        query = query.exclude(pk=exclude_session)
    return query.exists()


def slot_prompt(person):
    assign_counsellor(person)
    if not SessionRequest.objects.filter(participant=person, status="pending").exists():
        SessionRequest.objects.create(participant=person)
    slots = available_slots(person)
    person.booking_choices = [s.pk for s in slots]
    person.flow_state = "booking" if slots else "menu"
    if not slots:
        return ("Tumepokea request yako. No appointment times are available yet. "
                "Your request is waiting for staff to arrange a time; you can keep checking in.")
    lines = [f"{n}. {timezone.localtime(s.starts_at):%a %d %b, %H:%M} EAT" for n,s in enumerate(slots,1)]
    return "Hizi ndio available times (30 minutes):\n" + "\n".join(lines) + "\nReply na nambari, or choose Check in."


def book_appointment(person, user, starts_at, slot_id=None):
    from .services import queue_session_confirmation
    if starts_at <= timezone.now():
        raise ValueError("Choose a future appointment time.")
    with transaction.atomic():
        # Serialize booking and slot editing for this counsellor on PostgreSQL.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        slot = None
        if slot_id:
            slot = AvailabilitySlot.objects.select_for_update().filter(pk=slot_id, counsellor=user,
                    is_active=True, session__isnull=True, starts_at=starts_at).first()
            if not slot:
                raise ValueError("That time has just been taken. Please select another time.")
        if overlapping(user, starts_at):
            raise ValueError("That counsellor already has an appointment overlapping this time.")
        session = Session.objects.create(participant=person, counsellor=user, starts_at=starts_at)
        if slot:
            slot.session = session
            slot.save(update_fields=["session"])
        else:
            AvailabilitySlot.objects.filter(counsellor=user, starts_at=starts_at,
                                             session__isnull=True).update(session=session)
        SessionRequest.objects.filter(participant=person, status="pending").update(status="handled")
        queued = queue_session_confirmation(session)
        queue_staff_notice(person, user,
            f"MindBridge: {person.code} booked {timezone.localtime(starts_at):%d %b %H:%M} EAT. See Sessions.",
            f"staff-session:{session.pk}")
        return session, queued


def select_booking(person, command):
    if not command.isdigit() or not 1 <= int(command) <= len(person.booking_choices):
        return "Please choose one of the numbered appointment times, or choose Check in."
    slot = AvailabilitySlot.objects.filter(pk=person.booking_choices[int(command)-1],
                                          counsellor_id=person.counsellor_id).first()
    try:
        if not slot:
            raise ValueError("That appointment is no longer available.")
        session, _ = book_appointment(person, person.counsellor, slot.starts_at, slot.pk)
    except ValueError:
        return "That time is no longer available. " + slot_prompt(person)
    person.flow_state = "menu"
    person.booking_choices = []
    return f"Session yako is confirmed for {timezone.localtime(session.starts_at):%a %d %b at %H:%M} EAT. Reply here to request a change."


def run_escalations():
    from .services import queue_template, text_payload, SUPPORT
    count = 0
    due = RiskAlert.objects.filter(status="open", escalated_at__isnull=True,
                                  created_at__lte=timezone.now()-timedelta(hours=24))
    for pk in due.values_list("pk", flat=True):
        with transaction.atomic():
            alert = RiskAlert.objects.select_for_update().get(pk=pk)
            if alert.status != "open" or alert.escalated_at:
                continue
            alert.escalated_at = timezone.now()
            alert.save(update_fields=["escalated_at"])
            person = alert.participant
            for admin in get_user_model().objects.filter(is_staff=True, is_active=True):
                queue_staff_notice(person, admin, f"MindBridge: overdue alert for {person.code}; review admin dashboard.",
                                   f"escalation:{alert.pk}:admin:{admin.pk}")
            if person.consented and person.wa_id and not person.is_simulated:
                key = f"escalation:{alert.pk}:support"
                if person.last_inbound_at and person.last_inbound_at >= timezone.now()-timedelta(hours=23):
                    OutboundMessage.objects.get_or_create(dedupe_key=key, defaults={
                        "participant": person, "payload": text_payload(person.wa_id, SUPPORT)})
                else:
                    queue_template(person, settings.TURN_SUPPORT_TEMPLATE_NAME, key)
            count += 1
    return count


def enforce_retention(now=None):
    """Purge after twelve calendar months; delete requested profiles within thirty days."""
    now = now or timezone.now()
    try:
        cutoff = now.replace(year=now.year-1)
    except ValueError:  # 29 February
        cutoff = now.replace(year=now.year-1, day=28)
    moods = MoodEntry.objects.filter(recorded_at__lt=cutoff).delete()[0]
    InboundMessage.objects.filter(received_at__lt=cutoff).delete()
    OutboundMessage.objects.filter(created_at__lt=cutoff).delete()
    from .models import RiskEvidence
    RiskEvidence.objects.filter(recorded_at__lt=cutoff).delete()
    RiskAlert.objects.filter(created_at__lt=cutoff).delete()
    profiles = Participant.objects.filter(deletion_requested_at__lte=now-timedelta(days=29)).count()
    Participant.objects.filter(deletion_requested_at__lte=now-timedelta(days=29)).delete()
    return moods, profiles
