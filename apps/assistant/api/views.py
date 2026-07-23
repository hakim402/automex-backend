"""
apps/assistant/api/views.py
──────────────────────────────
Chat endpoint (API-key gated) + conversation history (JWT-authenticated).
The chat endpoint is throttled at its own "ai_assistant" scope since LLM
calls are more expensive than a typical write.
"""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.assistant import services
from apps.assistant.models import AIConversation, AIMessage
from apps.core.permissions import HasValidAPIKey, OptionalJWTAuthentication

from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ConversationHistorySerializer,
    ConversationListSerializer,
)


class ChatView(generics.GenericAPIView):
    authentication_classes = [OptionalJWTAuthentication]
    permission_classes = [HasValidAPIKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_assistant"
    serializer_class = ChatRequestSerializer

    @extend_schema(request=ChatRequestSerializer, responses=ChatResponseSerializer)
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user if request.user.is_authenticated else None

        result = services.handle_chat_message(
            request=request,
            session_id=data.get("session_id") or None,
            message=data["message"],
            language=data.get("language", "en"),
            page_url=data.get("page_url", ""),
            user=user,
        )

        return Response(ChatResponseSerializer(result).data, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# CONVERSATION HISTORY (JWT-authenticated)
# ──────────────────────────────────────────────────────────────────────────────


class ConversationListView(APIView):
    """GET /api/v1/assistant/conversations/ — list user's past conversations."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=ConversationListSerializer(many=True),
        summary="List my conversations",
    )
    def get(self, request):
        from django.db.models import Count, OuterRef, Subquery

        # Annotate so the serializer doesn't trigger N+1 queries.
        last_msg = AIMessage.objects.filter(
            conversation=OuterRef("pk"),
        ).order_by("-created_at")

        conversations = (
            AIConversation.objects.filter(user=request.user)
            .annotate(
                _message_count=Count("messages"),
                _last_role=Subquery(last_msg.values("role")[:1]),
                _last_content=Subquery(last_msg.values("content")[:1]),
                _last_created_at=Subquery(last_msg.values("created_at")[:1]),
            )
            .order_by("-started_at")[:50]
        )
        return Response(ConversationListSerializer(conversations, many=True).data)


class ConversationDetailView(APIView):
    """GET /api/v1/assistant/conversations/{id}/ — full transcript."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=ConversationHistorySerializer,
        summary="Conversation detail with messages",
    )
    def get(self, request, pk):
        try:
            conversation = AIConversation.objects.get(pk=pk, user=request.user)
        except AIConversation.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(ConversationHistorySerializer(conversation).data)
