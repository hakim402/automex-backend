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
