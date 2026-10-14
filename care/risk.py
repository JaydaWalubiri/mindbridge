from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from .models import Keyword, RiskEvidence
from .keywords import matches_keyword


def assess(person, text="", classification=None):
    now = timezone.now()
    entries = list(person.moods.filter(recorded_at__gte=now-timedelta(days=28)).order_by("-recorded_at"))
    weekly = {}
    for entry in entries:
        day = timezone.localtime(entry.recorded_at).date()
        week = day-timedelta(days=day.weekday())
        weekly.setdefault(week, entry.score)
    weeks = sorted(weekly, reverse=True)[:3]
    recent = bool(entries) and entries[0].recorded_at >= now-timedelta(days=7)
    low = (recent and len(weeks)==3 and weeks[0]-weeks[1]==timedelta(days=7)
           and weeks[1]-weeks[2]==timedelta(days=7) and all(weekly[w]<=2 for w in weeks))
    drop = recent and len(entries)>=2 and entries[1].score-entries[0].score>=3
    matches = [k for k in Keyword.objects.filter(is_active=True) if matches_keyword(text, k.term)]
    evidence = []
    if low:
        evidence.append(("behaviour", "Three consecutive low weekly check-ins"))
    if drop:
        evidence.append(("behaviour", "Mood dropped by three or more points"))
    if matches:
        evidence.extend(("keyword", "Matched phrase: " + keyword.term) for keyword in matches)
    if (classification and classification.risk_eligible and classification.label.casefold()=="negative"
        and classification.confidence>=settings.RISK_NEGATIVE_THRESHOLD):
        evidence.append(("sentiment", "Negative sentiment above configured threshold"))
    for layer, reason in evidence:
        if not person.risk_evidence.filter(layer=layer, reason=reason, recorded_at__gte=now-timedelta(days=1)).exists():
            RiskEvidence.objects.create(participant=person, layer=layer, reason=reason)
    if any(k.tier==1 for k in matches):
        return "high", "Urgent keyword review", "Tier-1 keyword override"
    if drop:
        return "high", "Sudden mood drop", "mood rule"
    if low:
        return "medium", "Consecutive low weekly moods", "mood rule"
    layers = set(person.risk_evidence.filter(recorded_at__gte=now-timedelta(days=7)).values_list("layer",flat=True))
    if not settings.SENTIMENT_RISK_ENABLED and not (classification and classification.risk_eligible):
        layers.discard("sentiment")
    if evidence and len(layers)>=2:
        return "medium", "Combined risk signals", ", ".join(sorted(layers))
    return None


def missed_checkin_signal(person, week):
    """Shared missed-week rule for the live scheduler and fictional test setup."""
    closed = list(person.weekly_checkins.filter(week_start__lt=week).order_by("-week_start")[:2])
    if (len(closed) == 2 and closed[0].week_start == week-timedelta(days=7)
            and closed[1].week_start == week-timedelta(days=14)
            and all(item.status == "missed" for item in closed)
            and not person.inbound_messages.filter(received_at__date__gte=closed[1].week_start,
                                                   received_at__date__lt=week).exists()):
        return "medium", "Two missed weekly check-ins", "weekly schedule"
    return None

