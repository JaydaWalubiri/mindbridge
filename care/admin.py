from django.contrib import admin
from .models import InboundMessage, Keyword, MoodEntry, OutboundMessage, Participant, RiskAlert, Session, SessionRequest, WeeklyCheckIn

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ("code", "display_name", "area", "counsellor")
    search_fields = ("code", "display_name")
    list_filter = ("area", "counsellor")

@admin.register(MoodEntry)
class MoodEntryAdmin(admin.ModelAdmin):
    list_display = ("participant", "score", "recorded_at", "sentiment_label")
    list_filter = ("score",)

@admin.register(RiskAlert)
class RiskAlertAdmin(admin.ModelAdmin):
    list_display = ("participant", "priority", "status", "created_at", "reviewed_by")
    list_filter = ("priority", "status")

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("participant", "counsellor", "starts_at", "status")
    list_filter = ("status",)

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("term", "language", "tier", "is_active")
    list_filter = ("language", "tier", "is_active")

@admin.register(InboundMessage)
class InboundMessageAdmin(admin.ModelAdmin):
    list_display = ("external_id", "participant", "received_at", "delivered")
    readonly_fields = ("external_id", "participant", "body", "received_at", "reply", "delivered")
    def has_add_permission(self, request):
        return False

@admin.register(SessionRequest)
class SessionRequestAdmin(admin.ModelAdmin):
    list_display = ("participant", "requested_at", "status")
    list_filter = ("status",)

@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("participant", "status", "attempts", "next_attempt_at", "sent_at")
    list_filter = ("status",)
    readonly_fields = ("participant", "inbound", "dedupe_key", "payload", "status", "attempts",
                       "next_attempt_at", "provider_message_id", "last_error", "created_at", "sent_at")
    def has_add_permission(self, request):
        return False

@admin.register(WeeklyCheckIn)
class WeeklyCheckInAdmin(admin.ModelAdmin):
    list_display = ("participant", "week_start", "status")
    list_filter = ("status", "week_start")
    readonly_fields = ("participant", "week_start", "status", "created_at")
    def has_add_permission(self, request):
        return False
