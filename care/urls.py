from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("alerts/", views.alerts, name="alerts"),
    path("alerts/<int:pk>/review/", views.review_alert, name="review_alert"),
    path("participants/", views.participants, name="participants"),
    path("participants/<int:pk>/", views.participant_detail, name="participant_detail"),
    path("participants/<int:pk>/sessions/new/", views.book_session, name="book_session"),
    path("sessions/", views.sessions, name="sessions"),
    path("workspace-admin/", views.admin_dashboard, name="admin_dashboard"),
    path("workspace-admin/requests/<int:pk>/handled/", views.handle_session_request, name="handle_session_request"),
    path("preview/whatsapp/", views.whatsapp_preview, name="whatsapp_preview"),
    path("webhooks/turn/", views.turn_webhook, name="turn_webhook"),
]
