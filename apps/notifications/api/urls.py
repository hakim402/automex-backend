"""
apps/notifications/api/urls.py
──────────────────────────────────
Mounted at /api/v1/notifications/ from config/urls.py.
"""
from __future__ import annotations

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", views.NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("<uuid:pk>/mark-read/", views.NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("mark-all-read/", views.NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("preferences/", views.NotificationPreferenceView.as_view(), name="notification-preferences"),
]
