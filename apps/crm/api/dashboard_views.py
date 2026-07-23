"""
apps/crm/api/dashboard_views.py
────────────────────────────────────
JWT-authenticated endpoints for registered users to manage their CRM data:
requests/leads, bookings, support tickets, and calculator estimates.
"""
from __future__ import annotations

import logging

from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema

from .. import services
from ..models import (
    CalculatorSubmission,
    ConsultationBooking,
    Lead,
    LeadActivity,
    SupportTicket,
    SupportTicketMessage,
)
from .dashboard_serializers import (
    CreateTicketSerializer,
    DashboardBookingSerializer,
    DashboardCalculationSerializer,
    DashboardLeadMessageSerializer,
    DashboardLeadSerializer,
    DashboardRescheduleSerializer,
    DashboardSummarySerializer,
    DashboardTicketListSerializer,
    DashboardTicketSerializer,
    SupportTicketMessageSerializer,
    TicketMessageCreateSerializer,
)

logger = logging.getLogger("apps.crm")


class DashboardMixin:
    """Common setup for all dashboard views."""
    permission_classes = [IsAuthenticated]


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD SUMMARY
# ──────────────────────────────────────────────────────────────────────────────


class DashboardSummaryView(DashboardMixin, APIView):
    """GET /api/v1/crm/dashboard/ — aggregated stats for the user."""

    @extend_schema(
        responses=DashboardSummarySerializer,
        summary="Dashboard summary stats",
    )
    def get(self, request):
        summary = services.get_user_dashboard_summary(request.user)
        return Response(DashboardSummarySerializer(summary).data)


# ──────────────────────────────────────────────────────────────────────────────
# REQUESTS / LEADS
# ──────────────────────────────────────────────────────────────────────────────


class DashboardRequestListView(DashboardMixin, generics.ListAPIView):
    """GET /api/v1/crm/dashboard/requests/ — list user's leads/requests."""

    serializer_class = DashboardLeadSerializer
    pagination_class = PageNumberPagination
    filterset_fields = ["status", "lead_type"]

    @extend_schema(
        responses=DashboardLeadSerializer(many=True),
        summary="List my requests",
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        from django.db.models import Prefetch
        from apps.content.models import Service
        return Lead.objects.filter(user=self.request.user)\
            .select_related("service_interest", "industry")\
            .prefetch_related(
                Prefetch("quote_detail__requested_services", queryset=Service.objects.all()),
            )\
            .order_by("-created_at")


class DashboardRequestDetailView(DashboardMixin, APIView):
    """GET /api/v1/crm/dashboard/requests/{id}/ — detail + activity timeline."""

    @extend_schema(
        responses=DashboardLeadSerializer,
        summary="Request detail",
    )
    def get(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk, user=request.user)
        except Lead.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        data = DashboardLeadSerializer(lead).data
        # Add activity timeline
        activities = lead.activities.filter(
            Q(is_customer_visible=True) | Q(performed_by=request.user)
        ).order_by("-created_at")[:50]
        from .dashboard_serializers import LeadActivitySerializer
        data["activities"] = LeadActivitySerializer(activities, many=True).data
        return Response(data)


class DashboardRequestMessageView(DashboardMixin, APIView):
    """POST /api/v1/crm/dashboard/requests/{id}/message/ — send message on a request."""

    @extend_schema(
        request=DashboardLeadMessageSerializer,
        summary="Send message on request",
    )
    def post(self, request, pk):
        try:
            lead = Lead.objects.get(pk=pk, user=request.user)
        except Lead.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DashboardLeadMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        LeadActivity.objects.create(
            lead=lead,
            activity_type=LeadActivity.ActivityType.OTHER,
            description=f"Message from {request.user}: {serializer.validated_data['message'][:200]}",
            message=serializer.validated_data["message"],
            is_customer_visible=True,
            performed_by=request.user,
        )

        return Response({"detail": "Message sent."}, status=status.HTTP_201_CREATED)


# ──────────────────────────────────────────────────────────────────────────────
# BOOKINGS
# ──────────────────────────────────────────────────────────────────────────────


class DashboardBookingListView(DashboardMixin, generics.ListAPIView):
    """GET /api/v1/crm/dashboard/bookings/ — list user's bookings."""

    serializer_class = DashboardBookingSerializer
    pagination_class = PageNumberPagination
    filterset_fields = ["status"]

    @extend_schema(
        responses=DashboardBookingSerializer(many=True),
        summary="List my bookings",
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return ConsultationBooking.objects.filter(user=self.request.user)\
            .select_related("lead", "slot")\
            .order_by("-scheduled_date")


class DashboardBookingDetailView(DashboardMixin, APIView):
    """GET /api/v1/crm/dashboard/bookings/{id}/ — booking detail."""

    @extend_schema(
        responses=DashboardBookingSerializer,
        summary="Booking detail",
    )
    def get(self, request, pk):
        try:
            booking = ConsultationBooking.objects.select_related("lead", "slot").get(pk=pk, user=request.user)
        except ConsultationBooking.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DashboardBookingSerializer(booking).data)


class DashboardBookingRescheduleView(DashboardMixin, APIView):
    """POST /api/v1/crm/dashboard/bookings/{id}/reschedule/ — request reschedule."""

    @extend_schema(
        request=DashboardRescheduleSerializer,
        summary="Request booking reschedule",
    )
    def post(self, request, pk):
        try:
            booking = ConsultationBooking.objects.select_related("lead").get(pk=pk, user=request.user)
        except ConsultationBooking.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if booking.status in [ConsultationBooking.Status.CANCELLED, ConsultationBooking.Status.COMPLETED]:
            return Response(
                {"detail": "Cannot reschedule a cancelled or completed booking."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = DashboardRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_date = serializer.validated_data["new_date"]
        new_time = serializer.validated_data["new_time"]
        reason = serializer.validated_data.get("reason", "Not specified")

        # Validate new date is not in the past
        if new_date < timezone.localdate():
            return Response(
                {"detail": "Cannot reschedule to a past date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_date = booking.scheduled_date
        old_time = booking.scheduled_time

        # Actually update the booking
        booking.scheduled_date = new_date
        booking.scheduled_time = new_time
        booking.reschedule_count += 1
        booking.status = ConsultationBooking.Status.RESCHEDULED
        booking.save(update_fields=["scheduled_date", "scheduled_time", "reschedule_count", "status", "updated_at"])

        LeadActivity.objects.create(
            lead=booking.lead,
            activity_type=LeadActivity.ActivityType.OTHER,
            description=(
                f"Rescheduled from {old_date} {old_time} to {new_date} {new_time}. "
                f"Reason: {reason}"
            ),
            performed_by=request.user,
        )

        return Response({"detail": "Booking rescheduled.", "new_date": new_date, "new_time": new_time})


class DashboardBookingCancelView(DashboardMixin, APIView):
    """POST /api/v1/crm/dashboard/bookings/{id}/cancel/ — cancel a booking."""

    @extend_schema(
        summary="Cancel booking",
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
    )
    def post(self, request, pk):
        try:
            booking = ConsultationBooking.objects.select_related("lead").get(pk=pk, user=request.user)
        except ConsultationBooking.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if booking.status in [ConsultationBooking.Status.CANCELLED, ConsultationBooking.Status.COMPLETED]:
            return Response(
                {"detail": "This booking is already cancelled or completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = ConsultationBooking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save(update_fields=["status", "cancelled_at", "updated_at"])

        if booking.lead:
            LeadActivity.objects.create(
                lead=booking.lead,
                activity_type=LeadActivity.ActivityType.OTHER,
                description=(
                    f"Booking #{booking.id} on {booking.scheduled_date} "
                    f"at {booking.scheduled_time} cancelled by client."
                ),
                performed_by=request.user,
            )

        return Response({"detail": "Booking cancelled."})


# ──────────────────────────────────────────────────────────────────────────────
# TICKETS
# ──────────────────────────────────────────────────────────────────────────────


class DashboardTicketListView(DashboardMixin, generics.ListCreateAPIView):
    """
    GET  /api/v1/crm/dashboard/tickets/ — list user's support tickets
    POST /api/v1/crm/dashboard/tickets/ — create new support ticket
    """

    pagination_class = PageNumberPagination
    filterset_fields = ["status", "ticket_type"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateTicketSerializer
        return DashboardTicketListSerializer

    @extend_schema(
        responses=DashboardTicketListSerializer(many=True),
        summary="List my tickets",
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @extend_schema(
        request=CreateTicketSerializer,
        responses=DashboardTicketSerializer,
        summary="Create support ticket",
    )
    def post(self, request, *args, **kwargs):
        serializer = CreateTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve related_lead from UUID if provided
        related_lead = None
        related_lead_id = data.get("related_lead")
        if related_lead_id:
            try:
                related_lead = Lead.objects.get(pk=related_lead_id, user=request.user)
            except Lead.DoesNotExist:
                pass

        ticket = services.create_support_ticket(
            title=data["title"],
            description=data["description"],
            ticket_type=data["ticket_type"],
            user=request.user,
            priority=data.get("priority", SupportTicket.Priority.NORMAL),
            related_lead=related_lead,
            related_service=data.get("related_service"),
        )

        return Response(
            DashboardTicketSerializer(ticket).data,
            status=status.HTTP_201_CREATED,
        )

    def get_queryset(self):
        from django.db.models import Count, Q
        return SupportTicket.objects.filter(user=self.request.user)\
            .annotate(_unread_count=Count("messages", filter=Q(messages__is_read=False)))\
            .order_by("-created_at")


class DashboardTicketDetailView(DashboardMixin, APIView):
    """GET /api/v1/crm/dashboard/tickets/{id}/ — ticket detail + messages."""

    @extend_schema(
        responses=DashboardTicketSerializer,
        summary="Ticket detail",
    )
    def get(self, request, pk):
        try:
            ticket = SupportTicket.objects.prefetch_related("messages").get(pk=pk, user=request.user)
        except SupportTicket.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        # Mark messages as read for this user
        ticket.messages.filter(is_read=False).exclude(author_user=request.user).update(is_read=True)

        return Response(DashboardTicketSerializer(ticket).data)


class DashboardTicketMessageView(DashboardMixin, APIView):
    """POST /api/v1/crm/dashboard/tickets/{id}/messages/ — reply to ticket."""

    @extend_schema(
        request=TicketMessageCreateSerializer,
        responses=SupportTicketMessageSerializer,
        summary="Reply to ticket",
    )
    def post(self, request, pk):
        try:
            ticket = SupportTicket.objects.get(pk=pk, user=request.user)
        except SupportTicket.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = TicketMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = services.add_ticket_message(
            ticket=ticket,
            body=serializer.validated_data["body"],
            author_user=request.user,
            author_name=str(request.user),
        )

        return Response(
            SupportTicketMessageSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


# ──────────────────────────────────────────────────────────────────────────────
# CALCULATIONS
# ──────────────────────────────────────────────────────────────────────────────


class DashboardCalculationListView(DashboardMixin, generics.ListAPIView):
    """GET /api/v1/crm/dashboard/calculations/ — user's past estimates."""

    serializer_class = DashboardCalculationSerializer
    pagination_class = PageNumberPagination

    @extend_schema(
        responses=DashboardCalculationSerializer(many=True),
        summary="List my calculations",
    )
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        return CalculatorSubmission.objects.filter(user=self.request.user)\
            .select_related("selected_service", "converted_lead")\
            .order_by("-created_at")


class DashboardCalculationConvertView(DashboardMixin, APIView):
    """POST /api/v1/crm/dashboard/calculations/{id}/convert/ — convert estimate to lead."""

    @extend_schema(
        responses=DashboardLeadSerializer,
        summary="Convert estimate to lead",
    )
    def post(self, request, pk):
        try:
            submission = CalculatorSubmission.objects.get(pk=pk, user=request.user)
        except CalculatorSubmission.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            lead = services.convert_estimate_to_lead(submission=submission, user=request.user)
        except ValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DashboardLeadSerializer(lead).data, status=status.HTTP_201_CREATED)
