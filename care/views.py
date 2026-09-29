import json
import uuid
from json import JSONDecodeError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import SessionForm
from .models import Keyword, OutboundMessage, Participant, RiskAlert, Session, SessionRequest
from .services import process_message, queue_session_confirmation, valid_turn_signature


def assigned(user):
    return Participant.objects.all() if user.is_staff else Participant.objects.filter(counsellor=user)


@login_required
def dashboard(request):
    people = assigned(request.user)
    open_alerts = RiskAlert.objects.filter(participant__in=people, status=RiskAlert.OPEN)
    context = {
        "active": "dashboard", "total_people": people.count(), "open_count": open_alerts.count(),
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
        alert.status = RiskAlert.REVIEWED
        alert.reviewed_at = timezone.now()
        alert.reviewed_by = request.user
        alert.save(update_fields=["status", "reviewed_at", "reviewed_by"])
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
    moods = list(person.moods.order_by("recorded_at"))
    return render(request, "care/participant.html", {
        "person": person, "active": "participants", "moods": reversed(moods[-8:]),
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
        session = form.save(commit=False)
        session.participant = person
        session.counsellor = person.counsellor if request.user.is_staff and person.counsellor_id else request.user
        session.save()
        SessionRequest.objects.filter(participant=person, status="pending").update(status="handled")
        queued = queue_session_confirmation(session)
        messages.success(request, "Session scheduled. Confirmation queued for WhatsApp." if queued else
                         "Session scheduled. Contact the participant to confirm the time; no approved template or recent conversation is available.")
        return redirect("sessions")
    return render(request, "care/book_session.html", {"person": person, "form": form, "active": "sessions"})


@staff_member_required
def admin_dashboard(request):
    return render(request, "care/admin_dashboard.html", {
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


def whatsapp_preview(request):
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
