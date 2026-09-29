from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Participant(models.Model):
    code = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=80)
    area = models.CharField(max_length=80, blank=True)
    counsellor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name="participants")
    created_at = models.DateTimeField(auto_now_add=True)
    wa_id = models.CharField(max_length=32, unique=True, null=True, blank=True,
                             help_text="WhatsApp sender ID; use a restricted database in real deployments.")
    consented = models.BooleanField(default=False)
    consented_at = models.DateTimeField(null=True, blank=True)
    last_inbound_at = models.DateTimeField(null=True, blank=True)
    preferred_language = models.CharField(max_length=12, default="en")
    flow_state = models.CharField(max_length=20, default="menu")

    def __str__(self):
        return f"{self.display_name} ({self.code})"


class MoodEntry(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="moods")
    score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    recorded_at = models.DateTimeField()
    note = models.TextField(blank=True)
    sentiment_label = models.CharField(max_length=32, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["recorded_at"]


class RiskAlert(models.Model):
    OPEN, REVIEWED = "open", "reviewed"
    STATUS = [(OPEN, "Needs review"), (REVIEWED, "Reviewed")]
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="alerts")
    status = models.CharField(max_length=10, choices=STATUS, default=OPEN)
    priority = models.CharField(max_length=12, choices=[("high", "High"), ("medium", "Medium")], default="medium")
    reason = models.CharField(max_length=180)
    trigger_source = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="reviewed_alerts")

    class Meta:
        ordering = ["-created_at"]


class Session(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="sessions")
    counsellor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=[("scheduled", "Scheduled"),
                               ("completed", "Completed"), ("cancelled", "Cancelled")], default="scheduled")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]


class Keyword(models.Model):
    term = models.CharField(max_length=120)
    language = models.CharField(max_length=30)
    tier = models.PositiveSmallIntegerField(default=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.term} ({self.language})"


class InboundMessage(models.Model):
    external_id = models.CharField(max_length=128, unique=True)
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="inbound_messages")
    body = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    reply = models.TextField(blank=True)
    delivered = models.BooleanField(default=False)

    class Meta:
        ordering = ["-received_at"]


class SessionRequest(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="session_requests")
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("handled", "Handled")], default="pending")

    class Meta:
        ordering = ["-requested_at"]


class OutboundMessage(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="outbound_messages")
    inbound = models.OneToOneField(InboundMessage, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="outbound_message")
    dedupe_key = models.CharField(max_length=180, unique=True)
    payload = models.JSONField()
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("sent", "Sent"),
                               ("failed", "Failed"), ("cancelled", "Cancelled")], default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    provider_message_id = models.CharField(max_length=128, blank=True)
    last_error = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]


class WeeklyCheckIn(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="weekly_checkins")
    week_start = models.DateField()
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("completed", "Completed"),
                               ("missed", "Missed")], default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["participant", "week_start"], name="unique_weekly_checkin")]
        ordering = ["-week_start"]
