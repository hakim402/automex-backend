"""
apps/notifications/api/views.py
───────────────────────────────────
JWT-authenticated endpoints for users to manage their notifications:
list, unread count, mark-read, mark-all-read, and preferences.
"""
from __future__ import annotations

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from ..models import Notification, NotificationPreference
from .serializers import (
    NotificationListSerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceUpdateSerializer,
    NotificationUnreadCountSerializer,
)

logger = logging.getLogger("apps.notifications")


class NotificationMixin:
    """Common setup for all notification views."""
    permission_classes = [IsAuthenticated]


# ──────────────────────────────────────────────────────────────────────────────
# NOTIFICATION LIST
# ──────────────────────────────────────────────────────────────────────────────


class NotificationListView(NotificationMixin, APIView):
    """GET /api/v1/notifications/ — list user's notifications."""

    @extend_schema(
        responses=NotificationListSerializer(many=True),
        summary="List my notifications",
    )
    def get(self, request):
        notifications = Notification.objects.filter(
            recipient_user=request.user,
        ).order_by("-created_at")[:100]

        return Response(NotificationListSerializer(notifications, many=True).data)


# ──────────────────────────────────────────────────────────────────────────────
# UNREAD COUNT
# ──────────────────────────────────────────────────────────────────────────────


class NotificationUnreadCountView(NotificationMixin, APIView):
    """GET /api/v1/notifications/unread-count/ — unread count for badge."""

    @extend_schema(
        responses=NotificationUnreadCountSerializer,
        summary="Unread notification count",
    )
    def get(self, request):
        count = Notification.objects.filter(
            recipient_user=request.user,
            is_read=False,
        ).count()
        return Response({"unread_count": count})


# ──────────────────────────────────────────────────────────────────────────────
# MARK READ
# ──────────────────────────────────────────────────────────────────────────────


class NotificationMarkReadView(NotificationMixin, APIView):
    """POST /api/v1/notifications/{id}/mark-read/ — mark single as read."""

    @extend_schema(
        summary="Mark notification as read",
    )
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, recipient_user=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])

        return Response({"detail": "Marked as read."})


class NotificationMarkAllReadView(NotificationMixin, APIView):
    """POST /api/v1/notifications/mark-all-read/ — mark all as read."""

    @extend_schema(
        summary="Mark all notifications as read",
    )
    def post(self, request):
        count = Notification.objects.filter(
            recipient_user=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())

        return Response({"detail": f"Marked {count} notification(s) as read."})


# ──────────────────────────────────────────────────────────────────────────────
# PREFERENCES
# ──────────────────────────────────────────────────────────────────────────────


class NotificationPreferenceView(NotificationMixin, APIView):
    """
    GET  /api/v1/notifications/preferences/ — get preferences
    PUT  /api/v1/notifications/preferences/ — update preferences
    """

    @extend_schema(
        responses=NotificationPreferenceSerializer(many=True),
        summary="Get notification preferences",
    )
    def get(self, request):
        prefs = NotificationPreference.objects.filter(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)

    @extend_schema(
        request=NotificationPreferenceUpdateSerializer,
        responses=NotificationPreferenceSerializer(many=True),
        summary="Update notification preferences",
    )
    def put(self, request):
        serializer = NotificationPreferenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for pref_data in serializer.validated_data["preferences"]:
            NotificationPreference.objects.update_or_create(
                user=request.user,
                event_type=pref_data["event_type"],
                channel=pref_data["channel"],
                defaults={
                    "is_enabled": pref_data.get("is_enabled", True),
                    "digest_frequency": pref_data.get("digest_frequency", "instant"),
                },
            )

        # Return updated preferences
        prefs = NotificationPreference.objects.filter(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)
