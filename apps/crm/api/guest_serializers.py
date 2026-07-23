"""
apps/crm/api/guest_serializers.py
──────────────────────────────────────
Serializers for guest tracking APIs. Guests use a tracking token to
look up their own requests and tickets.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import Service

from ..models import Lead, SupportTicket, SupportTicketMessage


# ──────────────────────────────────────────────────────────────────────────────
# GUEST REQUEST LOOKUP
# ──────────────────────────────────────────────────────────────────────────────


class GuestLeadSerializer(serializers.ModelSerializer):
    lead_type_display = serializers.CharField(source="get_lead_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    budget_range_display = serializers.CharField(source="get_budget_range_display", read_only=True)
    timeline_display = serializers.CharField(source="get_timeline_display", read_only=True)

    class Meta:
        model = Lead
        fields = [
            "id", "lead_type", "lead_type_display", "status", "status_display",
            "full_name", "email", "phone", "company", "job_title", "message",
            "service_interest", "industry",
            "budget_range", "budget_range_display", "timeline", "timeline_display",
            "guest_token", "created_at", "updated_at",
        ]
        read_only_fields = fields


class GuestLeadDetailSerializer(GuestLeadSerializer):
    """Extended serializer with activity timeline for guest view."""
    activities = serializers.SerializerMethodField()

    class Meta(GuestLeadSerializer.Meta):
        fields = GuestLeadSerializer.Meta.fields + ["activities"]

    def get_activities(self, obj):
        # Only show customer-visible activities
        activities = obj.activities.filter(is_customer_visible=True).order_by("-created_at")[:20]
        return [
            {
                "id": str(a.id),
                "activity_type": a.activity_type,
                "description": a.description,
                "message": a.message,
                "created_at": a.created_at.isoformat(),
            }
            for a in activities
        ]


# ──────────────────────────────────────────────────────────────────────────────
# GUEST TICKETS
# ──────────────────────────────────────────────────────────────────────────────


class GuestTicketMessageSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicketMessage
        fields = [
            "id", "author_name", "author_display",
            "author_is_staff", "body", "attachment", "attachment_url", "created_at",
        ]
        read_only_fields = fields

    def get_author_display(self, obj):
        if obj.author_user_id:
            return f"{obj.author_name} (Staff)" if obj.author_is_staff else obj.author_name
        return obj.author_name or "Guest"

    def get_attachment_url(self, obj):
        if obj.attachment and obj.attachment.file:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.attachment.file.url) if request else obj.attachment.file.url
        return None


class GuestTicketSerializer(serializers.ModelSerializer):
    ticket_type_display = serializers.CharField(source="get_ticket_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    messages = GuestTicketMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id", "title", "slug", "ticket_type", "ticket_type_display",
            "status", "status_display", "priority", "description",
            "related_service", "guest_email", "guest_token", "messages",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class GuestTicketListSerializer(serializers.ModelSerializer):
    ticket_type_display = serializers.CharField(source="get_ticket_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            "id", "title", "slug", "ticket_type", "ticket_type_display",
            "status", "status_display", "guest_token",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class GuestCreateTicketSerializer(serializers.Serializer):
    """For guests creating a support ticket."""
    title = serializers.CharField(max_length=250)
    description = serializers.CharField(max_length=10000)
    ticket_type = serializers.ChoiceField(choices=SupportTicket.TicketType.choices)
    guest_email = serializers.EmailField()
    priority = serializers.ChoiceField(
        choices=SupportTicket.Priority.choices,
        default=SupportTicket.Priority.NORMAL,
    )
    related_service = serializers.UUIDField(required=False, allow_null=True)


class GuestTicketMessageCreateSerializer(serializers.Serializer):
    """For guests adding a message to their ticket."""
    body = serializers.CharField(max_length=10000)
    author_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
