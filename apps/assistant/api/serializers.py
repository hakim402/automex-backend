"""
apps/assistant/api/serializers.py
──────────────────────────────────────
"""
from __future__ import annotations

from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    message = serializers.CharField(max_length=4000, trim_whitespace=True)
    language = serializers.CharField(max_length=10, required=False, default="en")
    page_url = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate_message(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        return value


class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    reply = serializers.CharField()
    lead_captured = serializers.BooleanField()
    lead_captured_this_turn = serializers.BooleanField()


# ──────────────────────────────────────────────────────────────────────────────
# CONVERSATION HISTORY (for authenticated users)
# ──────────────────────────────────────────────────────────────────────────────


class AIMessageHistorySerializer(serializers.Serializer):
    """Lightweight message serializer for conversation history."""
    id = serializers.UUIDField()
    role = serializers.CharField()
    content = serializers.CharField()
    created_at = serializers.DateTimeField()


class ConversationListSerializer(serializers.Serializer):
    """Summary serializer for conversation list view.

    Expects annotated _message_count, _last_role, _last_content,
    _last_created_at from the view's queryset — avoids N+1.
    """
    id = serializers.UUIDField()
    session_id = serializers.CharField()
    channel = serializers.CharField()
    language = serializers.CharField()
    lead_captured = serializers.BooleanField()
    started_at = serializers.DateTimeField()
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    def get_message_count(self, obj):
        return getattr(obj, "_message_count", 0)

    def get_last_message(self, obj):
        role = getattr(obj, "_last_role", None)
        if not role:
            return None
        return {
            "role": role,
            "content": (getattr(obj, "_last_content", "") or "")[:200],
            "created_at": getattr(obj, "_last_created_at", None),
        }


class ConversationHistorySerializer(serializers.Serializer):
    """Full conversation with all messages."""
    id = serializers.UUIDField()
    session_id = serializers.CharField()
    channel = serializers.CharField()
    language = serializers.CharField()
    lead_captured = serializers.BooleanField()
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField(allow_null=True)
    page_url = serializers.CharField()
    messages = AIMessageHistorySerializer(many=True, source="messages.all")
