"""
apps/crm/api/guest_views.py
──────────────────────────────
API-key gated endpoints for guest users to track their requests and
manage support tickets using a tracking token.
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from apps.core.permissions import HasValidAPIKey

from .. import services
from ..models import Lead, SupportTicket
from .guest_serializers import (
    GuestCreateTicketSerializer,
    GuestLeadDetailSerializer,
    GuestLeadSerializer,
    GuestTicketListSerializer,
    GuestTicketMessageCreateSerializer,
    GuestTicketMessageSerializer,
    GuestTicketSerializer,
)

logger = logging.getLogger("apps.crm")


class GuestMixin:
    """Common setup for all guest views."""
    authentication_classes = []
    permission_classes = [HasValidAPIKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_write"


# ──────────────────────────────────────────────────────────────────────────────
# GUEST REQUEST LOOKUP
# ──────────────────────────────────────────────────────────────────────────────


class GuestRequestListView(GuestMixin, APIView):
    """GET /api/v1/crm/guest/requests/?token=XXX — lookup guest requests by token."""

    @extend_schema(
        parameters=[{"name": "token", "in": "query", "required": True, "type": "string"}],
        responses=GuestLeadSerializer(many=True),
        summary="Lookup guest requests by tracking token",
    )
    def get(self, request):
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response(
                {"detail": "Query parameter 'token' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        leads = Lead.objects.filter(guest_token=token, user__isnull=True).order_by("-created_at")
        return Response(GuestLeadSerializer(leads, many=True).data)


class GuestRequestDetailView(GuestMixin, APIView):
    """GET /api/v1/crm/guest/requests/{id}/?token=XXX — guest request detail."""

    @extend_schema(
        parameters=[{"name": "token", "in": "query", "required": True, "type": "string"}],
        responses=GuestLeadDetailSerializer,
        summary="Guest request detail",
    )
    def get(self, request, pk):
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response(
                {"detail": "Query parameter 'token' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lead = Lead.objects.get(pk=pk, guest_token=token, user__isnull=True)
        except Lead.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(GuestLeadDetailSerializer(lead).data)


# ──────────────────────────────────────────────────────────────────────────────
# GUEST TICKETS
# ──────────────────────────────────────────────────────────────────────────────


class GuestTicketCreateView(GuestMixin, APIView):
    """POST /api/v1/crm/guest/tickets/ — guest creates support ticket."""

    @extend_schema(
        request=GuestCreateTicketSerializer,
        responses=GuestTicketSerializer,
        summary="Guest create support ticket",
    )
    def post(self, request):
        serializer = GuestCreateTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        ticket = services.create_support_ticket(
            title=data["title"],
            description=data["description"],
            ticket_type=data["ticket_type"],
            guest_email=data["guest_email"],
            priority=data.get("priority"),
        )

        # Return with the guest_token so the guest can track it
        response_data = GuestTicketSerializer(ticket).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class GuestTicketDetailView(GuestMixin, APIView):
    """GET /api/v1/crm/guest/tickets/{id}/?token=XXX — guest ticket detail."""

    @extend_schema(
        parameters=[{"name": "token", "in": "query", "required": True, "type": "string"}],
        responses=GuestTicketSerializer,
        summary="Guest ticket detail",
    )
    def get(self, request, pk):
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response(
                {"detail": "Query parameter 'token' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ticket = SupportTicket.objects.get(pk=pk, guest_token=token, user__isnull=True)
        except SupportTicket.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Mark staff messages as read
        ticket.messages.filter(is_read=False, author_is_staff=True).update(is_read=True)

        return Response(GuestTicketSerializer(ticket).data)


class GuestTicketMessageView(GuestMixin, APIView):
    """POST /api/v1/crm/guest/tickets/{id}/messages/?token=XXX — guest replies."""

    @extend_schema(
        parameters=[{"name": "token", "in": "query", "required": True, "type": "string"}],
        request=GuestTicketMessageCreateSerializer,
        responses=GuestTicketMessageSerializer,
        summary="Guest reply to ticket",
    )
    def post(self, request, pk):
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response(
                {"detail": "Query parameter 'token' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ticket = SupportTicket.objects.get(pk=pk, guest_token=token, user__isnull=True)
        except SupportTicket.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = GuestTicketMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        message = services.add_ticket_message(
            ticket=ticket,
            body=data["body"],
            author_name=data.get("author_name") or ticket.guest_email,
        )

        return Response(
            GuestTicketMessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )
