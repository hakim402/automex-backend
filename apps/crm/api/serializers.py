"""
apps/crm/api/serializers.py
────────────────────────────────
Input serializers validate what a public form can legitimately submit —
notably, server-side-only fields (ip_address, user_agent, referrer_url,
assigned_to, score, status transitions beyond "new") are never accepted
from the request body; apps.crm.services fills those in.

Output ("ack") serializers deliberately expose only what a public caller
needs to see (id, status, timestamps) — never internal pipeline fields
like `score`, `assigned_to`, or `notes`.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import Industry, Service

from ..models import AvailabilitySlot, ConsultationBooking, Lead, NewsletterSubscriber


# ──────────────────────────────────────────────────────────────────────────────
# SHARED LEAD FIELDS
# ──────────────────────────────────────────────────────────────────────────────

class LeadBaseFieldsSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    company = serializers.CharField(max_length=200, required=False, allow_blank=True)
    job_title = serializers.CharField(max_length=150, required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)

    service_interest = serializers.PrimaryKeyRelatedField(queryset=Service.objects.none(), required=False, allow_null=True)
    industry = serializers.PrimaryKeyRelatedField(queryset=Industry.objects.none(), required=False, allow_null=True)
    budget_range = serializers.ChoiceField(
        choices=Lead.BudgetRange.choices, required=False, default=Lead.BudgetRange.NOT_SPECIFIED,
    )
    timeline = serializers.ChoiceField(choices=Lead.Timeline.choices, required=False, allow_blank=True)

    utm_source = serializers.CharField(max_length=150, required=False, allow_blank=True)
    utm_medium = serializers.CharField(max_length=150, required=False, allow_blank=True)
    utm_campaign = serializers.CharField(max_length=150, required=False, allow_blank=True)
    utm_term = serializers.CharField(max_length=150, required=False, allow_blank=True)
    utm_content = serializers.CharField(max_length=150, required=False, allow_blank=True)
    source_page = serializers.CharField(max_length=500, required=False, allow_blank=True)
    language = serializers.CharField(max_length=10, required=False, default="en")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: Service.objects.published() filters on published_at__lte=now() —
        # that comparison value is computed the instant .published() is called.
        # Declaring it as a class-level `queryset=` default (Django/DRF's usual
        # pattern) would freeze "now" to whenever this module was first
        # imported (process startup), silently rejecting every service
        # published afterward. Reassigning here means it's evaluated fresh
        # on every serializer instantiation (i.e. every request).
        self.fields["service_interest"].queryset = Service.objects.published()
        self.fields["industry"].queryset = Industry.objects.filter(is_active=True)


# ──────────────────────────────────────────────────────────────────────────────
# CONTACT FORM
# ──────────────────────────────────────────────────────────────────────────────

class ContactLeadCreateSerializer(LeadBaseFieldsSerializer):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# QUOTE REQUEST
# ──────────────────────────────────────────────────────────────────────────────

class QuoteRequestCreateSerializer(LeadBaseFieldsSerializer):
    requested_services = serializers.PrimaryKeyRelatedField(queryset=Service.objects.none(), many=True, required=False)
    project_description = serializers.CharField(required=False, allow_blank=True)
    estimated_budget_min = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    estimated_budget_max = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    currency = serializers.CharField(max_length=3, required=False, default="USD")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requested_services"].child_relation.queryset = Service.objects.published()

    def validate(self, attrs):
        budget_min = attrs.get("estimated_budget_min")
        budget_max = attrs.get("estimated_budget_max")
        if budget_min is not None and budget_max is not None and budget_max < budget_min:
            raise serializers.ValidationError(
                {"estimated_budget_max": "Must be greater than or equal to estimated_budget_min."}
            )
        return attrs


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTATION BOOKING
# ──────────────────────────────────────────────────────────────────────────────

class ConsultationBookingCreateSerializer(LeadBaseFieldsSerializer):
    slot = serializers.PrimaryKeyRelatedField(queryset=AvailabilitySlot.objects.filter(is_active=True))
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField()
    meeting_type = serializers.ChoiceField(
        choices=ConsultationBooking.MeetingType.choices,
        required=False, default=ConsultationBooking.MeetingType.VIDEO,
    )
    timezone = serializers.CharField(max_length=64, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


# ──────────────────────────────────────────────────────────────────────────────
# NEWSLETTER
# ──────────────────────────────────────────────────────────────────────────────

class NewsletterSubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    language = serializers.CharField(max_length=10, required=False, default="en")
    source = serializers.CharField(max_length=500, required=False, allow_blank=True)


# ──────────────────────────────────────────────────────────────────────────────
# AVAILABILITY LOOKUP (read)
# ──────────────────────────────────────────────────────────────────────────────

class AvailableSlotSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="slot.id")
    weekday = serializers.IntegerField(source="slot.weekday")
    weekday_display = serializers.CharField(source="slot.get_weekday_display")
    start_time = serializers.TimeField(source="slot.start_time")
    end_time = serializers.TimeField(source="slot.end_time")
    timezone = serializers.CharField(source="slot.timezone")
    remaining_capacity = serializers.IntegerField()


# ──────────────────────────────────────────────────────────────────────────────
# RESPONSE ("ACK") SERIALIZERS — deliberately minimal
# ──────────────────────────────────────────────────────────────────────────────

class LeadAckSerializer(serializers.ModelSerializer):
    lead_type_display = serializers.CharField(source="get_lead_type_display", read_only=True)

    class Meta:
        model = Lead
        fields = ["id", "lead_type", "lead_type_display", "status", "created_at"]
        read_only_fields = fields


class ConsultationBookingAckSerializer(serializers.ModelSerializer):
    lead = LeadAckSerializer(read_only=True)

    class Meta:
        model = ConsultationBooking
        fields = ["id", "lead", "scheduled_date", "scheduled_time", "timezone", "meeting_type", "status"]
        read_only_fields = fields


class NewsletterSubscriberAckSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ["id", "email", "is_active", "subscribed_at"]
        read_only_fields = fields
