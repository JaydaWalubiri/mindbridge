from django.contrib import admin
from .models import InboundMessage, Keyword, MoodEntry, Participant, RiskAlert, Session, SessionRequest

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
