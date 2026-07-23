"""
apps/crm/api/dashboard_serializers.py
──────────────────────────────────────────
Serializers for authenticated user dashboard APIs. These expose
user-facing fields for their own CRM data — leads, bookings, tickets,
calculations — without leaking internal pipeline fields.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import Service

from ..models import (
    CalculatorSubmission,
    ConsultationBooking,
    Lead,
    LeadActivity,
    QuoteRequestDetail,
    SupportTicket,
    SupportTicketMessage,
)


# ──────────────────────────────────────────────────────────────────────────────
# LEADS / REQUESTS
# ──────────────────────────────────────────────────────────────────────────────


class LeadActivitySerializer(serializers.ModelSerializer):
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = LeadActivity
        fields = [
            "id", "activity_type", "description", "message",
            "is_customer_visible", "performed_by", "attachment", "attachment_url",
            "created_at",
        ]
        read_only_fields = fields

    def get_attachment_url(self, obj):
        if obj.attachment and obj.attachment.file:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.attachment.file.url) if request else obj.attachment.file.url
        return None


class QuoteRequestDetailSerializer(serializers.ModelSerializer):
    requested_service_names = serializers.SerializerMethodField()

    class Meta:
        model = QuoteRequestDetail
        fields = [
            "id", "requested_services", "requested_service_names",
            "project_description", "estimated_budget_min", "estimated_budget_max",
            "currency", "version", "quoted_price_min", "quoted_price_max",
            "quoted_currency",
        ]
        read_only_fields = fields

    def get_requested_service_names(self, obj):
        # Use prefetched data if available to avoid N+1
        if hasattr(obj, "_prefetched_objects_cache") and "requested_services" in obj._prefetched_objects_cache:
            return [s.safe_translation_getter("name", any_language=True) for s in obj._prefetched_objects_cache["requested_services"]]
        return list(obj.requested_services.values_list("translations__name", flat=True)[:10])


class DashboardLeadSerializer(serializers.ModelSerializer):
    lead_type_display = serializers.CharField(source="get_lead_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    budget_range_display = serializers.CharField(source="get_budget_range_display", read_only=True)
    timeline_display = serializers.CharField(source="get_timeline_display", read_only=True)
    source_channel_display = serializers.CharField(source="get_source_channel_display", read_only=True)
    quote_detail = QuoteRequestDetailSerializer(read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "lead_type", "lead_type_display", "status", "status_display",
            "priority", "priority_display", "full_name", "email", "phone",
            "company", "job_title", "service_interest", "industry",
            "message", "quote_detail",
            "budget_range", "budget_range_display", "timeline", "timeline_display",
            "source_channel", "source_channel_display",
            "guest_token", "tags", "expected_close_date",
            "lost_reason", "converted_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class DashboardLeadMessageSerializer(serializers.Serializer):
    """For sending a message on a lead (visible to staff)."""
    message = serializers.CharField(max_length=5000)


# ──────────────────────────────────────────────────────────────────────────────
# BOOKINGS
# ──────────────────────────────────────────────────────────────────────────────


class DashboardBookingSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    meeting_type_display = serializers.CharField(source="get_meeting_type_display", read_only=True)

    class Meta:
        model = ConsultationBooking
        fields = [
            "id", "lead", "scheduled_date", "scheduled_time", "timezone",
            "meeting_type", "meeting_type_display", "status", "status_display",
            "meeting_link", "calendar_event_link", "notes",
            "cancellation_reason", "reschedule_count",
            "confirmed_at", "cancelled_at", "completed_at", "created_at",
        ]
        read_only_fields = fields


class DashboardRescheduleSerializer(serializers.Serializer):
    """For requesting a reschedule of a booking."""
    new_date = serializers.DateField()
    new_time = serializers.TimeField()
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True)


# ──────────────────────────────────────────────────────────────────────────────
# TICKETS
# ──────────────────────────────────────────────────────────────────────────────


class SupportTicketMessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketMessage
        fields = [
            "id", "author_user", "author_name", "author_display",
            "author_is_staff", "body", "attachment", "attachment_url", "is_read", "created_at",
        ]
        read_only_fields = fields

    def get_author_display(self, obj):
        if obj.author_user_id:
            return str(obj.author_user)
        return obj.author_name or "Guest"

    def get_attachment_url(self, obj):
        if obj.attachment and obj.attachment.file:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.attachment.file.url) if request else obj.attachment.file.url
        return None


class DashboardTicketSerializer(serializers.ModelSerializer):
    ticket_type_display = serializers.CharField(source="get_ticket_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    messages = SupportTicketMessageSerializer(many=True, read_only=True)
    unread_message_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id", "title", "slug", "ticket_type", "ticket_type_display",
            "status", "status_display", "priority", "priority_display",
            "description", "assigned_to", "related_lead", "related_service",
            "resolution_summary", "resolved_at", "closed_at",
            "messages", "unread_message_count",
            "guest_token", "guest_email",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_unread_message_count(self, obj):
        # Use annotated value if available (from prefetch optimization)
        if hasattr(obj, "_unread_count"):
            return obj._unread_count
        return obj.messages.filter(is_read=False).count()


class DashboardTicketListSerializer(serializers.ModelSerializer):
    """Lighter serializer for ticket list views (no messages)."""
    ticket_type_display = serializers.CharField(source="get_ticket_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    unread_message_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            "id", "title", "slug", "ticket_type", "ticket_type_display",
            "status", "status_display", "priority", "priority_display",
            "description", "related_lead", "related_service", "guest_email",
            "assigned_to", "unread_message_count",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_unread_message_count(self, obj):
        # Use annotated value if available (from prefetch optimization)
        if hasattr(obj, "_unread_count"):
            return obj._unread_count
        return obj.messages.filter(is_read=False).count()


class CreateTicketSerializer(serializers.Serializer):
    """For creating a new support ticket."""
    title = serializers.CharField(max_length=250)
    description = serializers.CharField(max_length=10000)
    ticket_type = serializers.ChoiceField(choices=SupportTicket.TicketType.choices)
    priority = serializers.ChoiceField(
        choices=SupportTicket.Priority.choices,
        default=SupportTicket.Priority.NORMAL,
    )
    related_lead = serializers.UUIDField(required=False, allow_null=True)
    related_service = serializers.PrimaryKeyRelatedField(
        queryset=Service.objects.none(), required=False, allow_null=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["related_service"].queryset = Service.objects.published()


class TicketMessageCreateSerializer(serializers.Serializer):
    """For adding a message to a ticket."""
    body = serializers.CharField(max_length=10000)


# ──────────────────────────────────────────────────────────────────────────────
# CALCULATIONS
# ──────────────────────────────────────────────────────────────────────────────


class DashboardCalculationSerializer(serializers.ModelSerializer):
    service_name = serializers.SerializerMethodField()
    converted = serializers.BooleanField(source="converted_to_lead", read_only=True)

    class Meta:
        model = CalculatorSubmission
        fields = [
            "id", "selected_service", "service_name", "complexity_tier",
            "selected_features", "estimated_price_min", "estimated_price_max",
            "currency", "converted", "converted_lead",
            "created_at",
        ]
        read_only_fields = fields

    def get_service_name(self, obj):
        if obj.selected_service:
            return str(obj.selected_service)
        return ""


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD SUMMARY
# ──────────────────────────────────────────────────────────────────────────────


class DashboardSummarySerializer(serializers.Serializer):
    total_requests = serializers.IntegerField()
    active_requests = serializers.IntegerField()
    total_bookings = serializers.IntegerField()
    upcoming_bookings = serializers.IntegerField()
    total_tickets = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
    total_calculations = serializers.IntegerField()
