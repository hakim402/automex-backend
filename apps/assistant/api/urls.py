"""
apps/assistant/api/urls.py
─────────────────────────────
Mounted at /api/v1/assistant/ from config/urls.py.
"""
from __future__ import annotations

from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("chat/", views.ChatView.as_view(), name="chat"),
]
