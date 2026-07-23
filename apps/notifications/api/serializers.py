"""
apps/notifications/api/serializers.py
─────────────────────────────────────────
Serializers for user notification APIs — list, unread count, mark-read,
and preferences management.
"""
from __future__ import annotations

from rest_framework import serializers

from ..models import (
    Notification,
    NotificationChannel,
    NotificationEventType,
    NotificationPreference,
)


class NotificationListSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "event_type", "event_type_display", "channel", "channel_display",
            "subject", "body", "priority", "priority_display",
            "status", "status_display", "is_read",
            "created_at", "sent_at", "read_at",
        ]
        read_only_fields = fields


class NotificationUnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class MarkReadSerializer(serializers.Serializer):
    """No input needed — marks the specific notification as read."""
    pass


class MarkAllReadSerializer(serializers.Serializer):
    """No input needed — marks all notifications as read."""
    pass


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            "id", "event_type", "event_type_display", "channel", "channel_display",
            "is_enabled", "digest_frequency",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class NotificationPreferenceUpdateSerializer(serializers.Serializer):
    """Bulk update notification preferences."""
    preferences = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of {event_type, channel, is_enabled, digest_frequency} dicts.",
    )

    def validate_preferences(self, value):
        valid_event_types = set(NotificationEventType.values)
        valid_channels = set(NotificationChannel.values)
        valid_digest_frequencies = {"instant", "daily", "weekly"}

        for pref in value:
            if "event_type" not in pref or "channel" not in pref:
                raise serializers.ValidationError(
                    "Each preference must include 'event_type' and 'channel'."
                )
            if pref["event_type"] not in valid_event_types:
                raise serializers.ValidationError(
                    f"Invalid event_type: {pref['event_type']}"
                )
            if pref["channel"] not in valid_channels:
                raise serializers.ValidationError(
                    f"Invalid channel: {pref['channel']}"
                )
            # Validate is_enabled type
            if "is_enabled" in pref and not isinstance(pref["is_enabled"], bool):
                raise serializers.ValidationError(
                    f"'is_enabled' must be a boolean, got: {pref['is_enabled']}"
                )
            # Validate digest_frequency value
            if "digest_frequency" in pref and pref["digest_frequency"] not in valid_digest_frequencies:
                raise serializers.ValidationError(
                    f"Invalid digest_frequency: {pref['digest_frequency']}. "
                    f"Must be one of: {', '.join(sorted(valid_digest_frequencies))}"
                )
        return value
