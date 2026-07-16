"""
apps/assistant/api/views.py
──────────────────────────────
Single chat endpoint. API-key gated (same posture as content/crm), throttled
at its own "ai_assistant" scope since LLM calls are more expensive than a
typical write.
"""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.assistant import services
from apps.core.permissions import HasValidAPIKey

from .serializers import ChatRequestSerializer, ChatResponseSerializer

from drf_spectacular.utils import extend_schema


class ChatView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [HasValidAPIKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_assistant"
    serializer_class = ChatRequestSerializer

    @extend_schema(request=ChatRequestSerializer, responses=ChatResponseSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = services.handle_chat_message(
            request=request,
            session_id=data.get("session_id") or None,
            message=data["message"],
            language=data.get("language", "en"),
            page_url=data.get("page_url", ""),
        )

        return Response(ChatResponseSerializer(result).data, status=status.HTTP_200_OK)
