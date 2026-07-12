"""
apps/crm/api/views.py
────────────────────────
Public write endpoints. API-key gated (same X-API-Key as the content API),
throttled at the stricter "public_write" scope, views stay thin — all
business logic lives in apps.crm.services.
"""
from __future__ import annotations

from datetime import date as date_cls

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.permissions import HasValidAPIKey

from .. import services
from .serializers import (
    AvailableSlotSerializer,
    ConsultationBookingAckSerializer,
    ConsultationBookingCreateSerializer,
    ContactLeadCreateSerializer,
    LeadAckSerializer,
    NewsletterSubscribeSerializer,
    NewsletterSubscriberAckSerializer,
    QuoteRequestCreateSerializer,
)


class PublicWriteMixin:
    authentication_classes = []
    permission_classes = [HasValidAPIKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_write"


class PublicReadMixin:
    authentication_classes = []
    permission_classes = [HasValidAPIKey]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_content"


# ──────────────────────────────────────────────────────────────────────────────
# CONTACT FORM
# ──────────────────────────────────────────────────────────────────────────────

class ContactLeadCreateView(PublicWriteMixin, generics.GenericAPIView):
    serializer_class = ContactLeadCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = services.capture_contact_lead(request=request, validated_data=serializer.validated_data)
        return Response(LeadAckSerializer(lead).data, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# QUOTE REQUEST
# ──────────────────────────────────────────────────────────────────────────────

class QuoteRequestCreateView(PublicWriteMixin, generics.GenericAPIView):
    serializer_class = QuoteRequestCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = services.capture_quote_lead(request=request, validated_data=serializer.validated_data)
        return Response(LeadAckSerializer(lead).data, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTATION BOOKING
# ──────────────────────────────────────────────────────────────────────────────

class ConsultationBookingCreateView(PublicWriteMixin, generics.GenericAPIView):
    serializer_class = ConsultationBookingCreateSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = services.book_consultation(request=request, validated_data=serializer.validated_data)
        return Response(ConsultationBookingAckSerializer(booking).data, status=status.HTTP_201_CREATED)


class AvailableSlotsView(PublicReadMixin, APIView):
    """GET ?date=YYYY-MM-DD → open slots + remaining capacity for that date."""

    def get(self, request, *args, **kwargs):
        date_param = request.query_params.get("date")
        if not date_param:
            return Response({"detail": "Query param 'date' (YYYY-MM-DD) is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = date_cls.fromisoformat(date_param)
        except ValueError:
            return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        results = services.available_slots_for_date(target_date)
        serializer = AvailableSlotSerializer(results, many=True)
        return Response(serializer.data)


# ──────────────────────────────────────────────────────────────────────────────
# NEWSLETTER
# ──────────────────────────────────────────────────────────────────────────────

class NewsletterSubscribeView(PublicWriteMixin, generics.GenericAPIView):
    serializer_class = NewsletterSubscribeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscriber = services.subscribe_newsletter(request=request, validated_data=serializer.validated_data)
        return Response(NewsletterSubscriberAckSerializer(subscriber).data, status=status.HTTP_201_CREATED)
