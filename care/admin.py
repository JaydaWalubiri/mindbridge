from django.contrib import admin
from django.utils import timezone
from .models import InboundMessage, Keyword, MoodEntry, OutboundMessage, Participant, RiskAlert, Session, SessionRequest, WeeklyCheckIn

class ReadOnlyRecords(admin.ModelAdmin):
    """Operational inspection never substitutes for counsellor case actions."""
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    actions = ["delete_selected"]

    def get_readonly_fields(self, request, obj=None):
        return ("code", "created_at", "consented_at", "minor_assent_at", "last_inbound_at", "deletion_requested_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return bool(request.user and (request.user.is_staff or request.user.is_superuser))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "counsellor":
            from django.contrib.auth import get_user_model
            kwargs["queryset"] = get_user_model().objects.filter(is_active=True, is_staff=False, care_profile__isnull=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    list_display = ("code", "display_name", "age", "area", "is_simulated", "counsellor")
    search_fields = ("code", "display_name", "area")
    list_filter = ("area", "counsellor", "is_simulated")

@admin.register(MoodEntry)
class MoodEntryAdmin(ReadOnlyRecords):
    list_display = ("participant", "score", "recorded_at", "sentiment_label")
    list_filter = ("score",)

@admin.register(RiskAlert)
class RiskAlertAdmin(ReadOnlyRecords):
    readonly_fields = ("matched_terms",)
    list_display = ("participant", "priority", "reason", "trigger_source", "status", "created_at", "reviewed_by")
    list_filter = ("priority", "status")

@admin.register(Session)
class SessionAdmin(ReadOnlyRecords):
    list_display = ("participant", "counsellor", "starts_at", "status")
    list_filter = ("status",)

@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ("term", "language", "category", "tier", "is_active")
    list_filter = ("language", "category", "tier", "is_active")

@admin.register(InboundMessage)
class InboundMessageAdmin(ReadOnlyRecords):
    list_display = ("external_id", "participant", "received_at", "delivered")
    readonly_fields = ("external_id", "participant", "body", "received_at", "reply", "delivered", "sentiment_label", "sentiment_score", "sentiment_source", "sentiment_risk_eligible")
    def has_add_permission(self, request):
        return False

@admin.register(SessionRequest)
class SessionRequestAdmin(ReadOnlyRecords):
    list_display = ("participant", "requested_at", "status")
    list_filter = ("status",)

@admin.register(OutboundMessage)
class OutboundMessageAdmin(admin.ModelAdmin):
    list_display = ("participant", "status", "attempts", "next_attempt_at", "sent_at")
    list_filter = ("status",)
    readonly_fields = ("participant", "inbound", "dedupe_key", "payload", "status", "attempts",
                       "next_attempt_at", "provider_message_id", "last_error", "created_at", "sent_at")
    actions = ["retry_failed"]

    @admin.action(description="Retry selected failed messages")
    def retry_failed(self, request, queryset):
        count = queryset.filter(status="failed").update(status="pending", attempts=0,
                                                          next_attempt_at=timezone.now(), last_error="")
        self.message_user(request, f"Queued {count} failed messages for retry.")
    def has_add_permission(self, request):
        return False

@admin.register(WeeklyCheckIn)
class WeeklyCheckInAdmin(ReadOnlyRecords):
    list_display = ("participant", "week_start", "status")
    list_filter = ("status", "week_start")
    readonly_fields = ("participant", "week_start", "status", "created_at")
    def has_add_permission(self, request):
        return False


from .models import AssignmentRotation, AvailabilitySlot, CounsellorProfile, RiskEvidence


@admin.register(CounsellorProfile)
class CounsellorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_simulated", "accepts_assignments", "notification_opt_in")
    list_filter = ("is_simulated", "accepts_assignments",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            from django.contrib.auth import get_user_model
            kwargs["queryset"] = get_user_model().objects.filter(is_staff=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(ReadOnlyRecords):
    list_display = ("counsellor", "starts_at", "is_active", "session")
    list_filter = ("counsellor", "is_active")

    def has_add_permission(self, request):
        # Slot creation goes through overlap validation in the counsellor UI.
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RiskEvidence)
class RiskEvidenceAdmin(ReadOnlyRecords):
    list_display = ("participant", "layer", "reason", "recorded_at")
    readonly_fields = ("participant", "layer", "reason", "recorded_at")
    def has_add_permission(self, request):
        return False
