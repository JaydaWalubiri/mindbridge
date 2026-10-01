import json
import uuid
from json import JSONDecodeError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from datetime import timedelta
from django.http import HttpResponseNotAllowed, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import SessionForm, AvailabilityForm
from .models import AvailabilitySlot, CounsellorProfile, Keyword, OutboundMessage, Participant, RiskAlert, Session, SessionRequest
from .services import process_message, queue_session_confirmation, valid_turn_signature


def assigned(user):
    return Participant.objects.all() if user.is_staff else Participant.objects.filter(counsellor=user)


@login_required
def dashboard(request):
    people = assigned(request.user)
    open_alerts = RiskAlert.objects.filter(participant__in=people, status=RiskAlert.OPEN)
    pending = SessionRequest.objects.filter(participant__in=people, status="pending").select_related("participant")
    context = {
        "pending_requests": pending[:8], "request_count": pending.count(), "active": "dashboard", "total_people": people.count(), "open_count": open_alerts.count(),
        "upcoming_count": Session.objects.filter(participant__in=people, status="scheduled", starts_at__gte=timezone.now()).count(),
        "recent_alerts": open_alerts.select_related("participant")[:6],
        "upcoming_sessions": Session.objects.filter(participant__in=people, status="scheduled",
                                                    starts_at__gte=timezone.now()).select_related("participant")[:4],
    }
    return render(request, "care/dashboard.html", context)


@login_required
def alerts(request):
    status = request.GET.get("status", "open")
    if status not in ("open", "reviewed", "all"):
        status = "open"
    items = RiskAlert.objects.filter(participant__in=assigned(request.user)).select_related("participant", "reviewed_by")
    if status != "all":
        items = items.filter(status=status)
    return render(request, "care/alerts.html", {"alerts": items, "status": status, "active": "alerts"})


@login_required
@require_POST
def review_alert(request, pk):
    alert = get_object_or_404(RiskAlert, pk=pk, participant__in=assigned(request.user))
    if alert.status == RiskAlert.OPEN:
        outcome = request.POST.get("outcome", "follow_up")
        if outcome not in ("concern_confirmed", "false_positive", "follow_up"):
            return JsonResponse({"error": "Invalid review outcome"}, status=400)
        alert.outcome = outcome
        alert.review_note = request.POST.get("review_note", "").strip()[:2000]
        alert.status = RiskAlert.REVIEWED
        alert.reviewed_at = timezone.now()
        alert.reviewed_by = request.user
        alert.save(update_fields=["status", "reviewed_at", "reviewed_by", "outcome", "review_note"])
        messages.success(request, "Alert marked as reviewed.")
    return redirect("alerts")


@login_required
def participants(request):
    q = request.GET.get("q", "").strip()
    people = assigned(request.user)
    if q:
        people = people.filter(Q(code__icontains=q) | Q(display_name__icontains=q))
    return render(request, "care/participants.html", {"people": people.order_by("display_name"), "q": q, "active": "participants"})


@login_required
def participant_detail(request, pk):
    person = get_object_or_404(assigned(request.user), pk=pk)
    moods = list(person.moods.filter(recorded_at__gte=timezone.now()-timedelta(days=28)).order_by("recorded_at"))
    return render(request, "care/participant.html", {
        "person": person, "chat_entries": person.inbound_messages.all()[:8], "active": "participants", "moods": reversed(moods[-8:]),
        "chart_labels": json.dumps([m.recorded_at.strftime("%d %b") for m in moods[-12:]]),
        "chart_scores": json.dumps([m.score for m in moods[-12:]]),
        "alerts": person.alerts.all()[:5], "sessions": person.sessions.all()[:5],
    })


@login_required
def sessions(request):
    items = Session.objects.filter(participant__in=assigned(request.user)).select_related("participant", "counsellor")
    return render(request, "care/sessions.html", {"sessions": items, "active": "sessions"})


@login_required
def book_session(request, pk):
    person = get_object_or_404(assigned(request.user), pk=pk)
    form = SessionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        from .workflows import book_appointment
        user = person.counsellor if request.user.is_staff and person.counsellor_id else request.user
        try:
            session, queued = book_appointment(person, user, form.cleaned_data["starts_at"])
        except ValueError as error:
            form.add_error("starts_at", str(error))
        else:
            messages.success(request, "Session scheduled. Confirmation queued for WhatsApp." if queued else
                             "Session scheduled. Confirm manually if this is a live participant; WhatsApp confirmation is not configured.")
            return redirect("sessions")
    return render(request, "care/book_session.html", {"person": person, "form": form, "active": "sessions"})


@staff_member_required
def admin_dashboard(request):
    return render(request, "care/admin_dashboard.html", {
        "overdue_alerts": RiskAlert.objects.filter(status="open", created_at__lte=timezone.now()-timedelta(hours=24)).select_related("participant"),
        "unassigned": Participant.objects.filter(onboarding_complete=True, counsellor__isnull=True),
        "reviewed_count": RiskAlert.objects.filter(status="reviewed").count(),
        "all_alert_count": RiskAlert.objects.count(),
        "deletion_requests": Participant.objects.filter(deletion_requested_at__isnull=False),
        "staff_template_ready": bool(settings.TURN_STAFF_TEMPLATE_NAME and settings.TURN_TEMPLATE_NAMESPACE),
        "support_template_ready": bool(settings.TURN_SUPPORT_TEMPLATE_NAME and settings.TURN_TEMPLATE_NAMESPACE),
        "active": "admin", "participants_count": Participant.objects.count(),
        "staff_count": get_user_model().objects.filter(is_staff=True).count(),
        "pending_count": SessionRequest.objects.filter(status="pending").count(),
        "open_count": RiskAlert.objects.filter(status="open").count(),
        "pending": SessionRequest.objects.filter(status="pending").select_related("participant")[:8],
        "keywords": Keyword.objects.filter(is_active=True).count(),
        "outbound_pending": OutboundMessage.objects.filter(status="pending").count(),
        "outbound_failed": OutboundMessage.objects.filter(status="failed").count(),
        "turn_ready": bool(settings.TURN_WEBHOOK_SECRET and settings.TURN_API_TOKEN),
        "template_ready": bool(settings.TURN_TEMPLATE_NAMESPACE and settings.TURN_CHECKIN_TEMPLATE_NAME),
    })


@login_required
def whatsapp_preview(request):
    if not settings.DEBUG:
        raise Http404("Local simulator is disabled outside development.")
    if not request.user.is_staff:
        raise Http404()
    return render(request, "care/whatsapp_preview.html")


@csrf_exempt
def turn_webhook(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if len(request.body) > 1024 * 1024:
        return JsonResponse({"error": "payload too large"}, status=413)
    if not valid_turn_signature(request.body, request.headers.get("X-Turn-Hook-Signature", "")):
        return JsonResponse({"error": "invalid signature"}, status=403)
    if request.headers.get("X-Turn-Hook-Subscription") != "whatsapp":
        return JsonResponse({"received": 0})
    try:
        payload = json.loads(request.body)
    except (JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid json"}, status=400)
    if not isinstance(payload, dict) or not isinstance(payload.get("messages", []), list):
        return JsonResponse({"error": "invalid messages"}, status=400)
    processed = 0
    for message in payload.get("messages", [])[:25]:
        if not isinstance(message, dict):
            continue
        if message.get("type") not in ("text", "interactive") or not message.get("id") or not message.get("from"):
            continue
        if message["type"] == "interactive":
            choice = message.get("interactive", {}).get("button_reply") or message.get("interactive", {}).get("list_reply") or {}
            body = choice.get("id") or choice.get("title", "")
        else:
            body = message.get("text", {}).get("body", "")
        if not isinstance(body, str) or not body.strip():
            continue
        wa_id = str(message["from"])[:32]
        person, _ = Participant.objects.get_or_create(wa_id=wa_id, defaults={
            "code": "MB-" + uuid.uuid4().hex[:12].upper(),
            "display_name": "Participant " + uuid.uuid4().hex[:6].upper(),
        })
        process_message(person, body, str(message["id"])[:128])
        processed += 1
    return JsonResponse({"received": processed})


@login_required
def availability(request):
    from .workflows import overlapping
    form = AvailabilityForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            slot_user = form.cleaned_data.get("counsellor") or request.user
            get_user_model().objects.select_for_update().get(pk=slot_user.pk)
            when = form.cleaned_data["starts_at"]
            slots = AvailabilitySlot.objects.filter(counsellor=slot_user, is_active=True,
                starts_at__gt=when-timedelta(minutes=30), starts_at__lt=when+timedelta(minutes=30))
            if overlapping(slot_user, when) or slots.exists():
                form.add_error("starts_at", "This time overlaps an appointment or an existing available slot.")
            else:
                AvailabilitySlot.objects.update_or_create(counsellor=slot_user, starts_at=when,
                                                         defaults={"is_active": True})
                messages.success(request, "Available appointment time added.")
                return redirect("availability")
    return render(request, "care/availability.html", {"active": "availability", "form": form,
        "slots": AvailabilitySlot.objects.filter(starts_at__gt=timezone.now()).filter(Q(counsellor=request.user) if not request.user.is_staff else Q()).select_related("counsellor")})


@login_required
@require_POST
def remove_availability(request, pk):
    slot = get_object_or_404(AvailabilitySlot.objects.all() if request.user.is_staff else AvailabilitySlot.objects.filter(counsellor=request.user), pk=pk)
    if slot.session_id:
        messages.error(request, "Cancel the booked appointment before removing this time.")
    else:
        slot.is_active = False
        slot.save(update_fields=["is_active"])
    return redirect("availability")


@login_required
@require_POST
def update_session(request, pk):
    session = get_object_or_404(Session, pk=pk, participant__in=assigned(request.user))
    status = request.POST.get("status")
    if status not in ("completed", "cancelled"):
        return JsonResponse({"error": "Invalid session status"}, status=400)
    if session.status == "scheduled":
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=session.counsellor_id)
            session = Session.objects.select_for_update().get(pk=pk)
            if session.status == "scheduled":
                session.status = status
                session.save(update_fields=["status"])
                AvailabilitySlot.objects.filter(session=session).update(session=None, is_active=False)
                # An existing confirmation must not be delivered after a cancellation.
                OutboundMessage.objects.filter(dedupe_key__in=[f"session:{pk}", f"staff-session:{pk}"],
                                               status="pending").update(status="cancelled")
                messages.success(request, f"Session {status}. Contact the participant to confirm any change.")
    return redirect("sessions")


@staff_member_required
@require_POST
def assign_waiting(request):
    from .workflows import assign_counsellor
    count = 0
    with transaction.atomic():
        for person in Participant.objects.select_for_update().filter(onboarding_complete=True,
                consented=True, counsellor__isnull=True, deletion_requested_at__isnull=True):
            count += bool(assign_counsellor(person))
    messages.success(request, f"Assigned {count} waiting participants to eligible counsellors.")
    return redirect("admin_dashboard")


@login_required
@require_POST
def simulator_message(request):
    if not settings.DEBUG or not request.user.is_staff:
        raise Http404()
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request"}, status=400)
    if not isinstance(data, dict) or not isinstance(data.get("body", ""), str):
        return JsonResponse({"error": "Invalid message"}, status=400)
    body = data.get("body", "").strip()[:1000]
    if not body:
        return JsonResponse({"error": "Write a message first"}, status=400)
    key = "simulated_participant_id"
    person = Participant.objects.filter(pk=request.session.get(key), is_simulated=True).first()
    if not person or data.get("reset"):
        # Keep previous demo records for reviewing the dashboard.
        person = Participant.objects.create(code="DEMO-CHAT-"+uuid.uuid4().hex[:10].upper(),
                    display_name="Demo participant", is_simulated=True)
        request.session[key] = person.pk
    incoming, _ = process_message(person, body, "demo:"+uuid.uuid4().hex)
    person.refresh_from_db()
    return JsonResponse({"reply": incoming.reply, "buttons": getattr(incoming, "suggested_buttons", ()),
        "code": person.code, "profile_url": f"/participants/{person.pk}/", "state": person.flow_state,
        "assigned_to": person.counsellor.get_full_name() or person.counsellor.username if person.counsellor_id else "Awaiting assignment"})
