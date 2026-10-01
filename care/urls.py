from django.urls import path
from . import views

urlpatterns = [
    path("availability/", views.availability, name="availability"),
    path("availability/<int:pk>/remove/", views.remove_availability, name="remove_availability"),
    path("sessions/<int:pk>/status/", views.update_session, name="update_session"),
    path("workspace-admin/assign/", views.assign_waiting, name="assign_waiting"),
    path("preview/whatsapp/message/", views.simulator_message, name="simulator_message"),
    path("", views.dashboard, name="dashboard"),
    path("alerts/", views.alerts, name="alerts"),
    path("alerts/<int:pk>/review/", views.review_alert, name="review_alert"),
    path("participants/", views.participants, name="participants"),
    path("participants/<int:pk>/", views.participant_detail, name="participant_detail"),
    path("participants/<int:pk>/sessions/new/", views.book_session, name="book_session"),
    path("sessions/", views.sessions, name="sessions"),
    path("workspace-admin/", views.admin_dashboard, name="admin_dashboard"),
    path("preview/whatsapp/", views.whatsapp_preview, name="whatsapp_preview"),
    path("webhooks/turn/", views.turn_webhook, name="turn_webhook"),
]
