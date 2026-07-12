"""
apps/crm/admin.py
────────────────────
Unfold admin registrations for the sales pipeline: Lead (+ QuoteRequestDetail
/ LeadActivity inlines), NewsletterSubscriber, AvailabilitySlot,
ConsultationBooking, CostCalculatorRule, CalculatorSubmission.
"""
from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.core.admin_mixins import ActiveToggleAdminMixin

from .models import (
    AvailabilitySlot,
    CalculatorSubmission,
    ConsultationBooking,
    CostCalculatorRule,
    Lead,
    LeadActivity,
    NewsletterSubscriber,
    QuoteRequestDetail,
)


def _initials(text: str) -> str:
    parts = [p for p in (text or "").split() if p]
    if not parts:
        return "?"
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()


# ──────────────────────────────────────────────────────────────────────────────
# INLINES
# ──────────────────────────────────────────────────────────────────────────────


class QuoteRequestDetailInline(StackedInline):
    model = QuoteRequestDetail
    extra = 0
    tab = True
    can_delete = False
    filter_horizontal = ["requested_services"]
    fields = [
        "requested_services",
        "project_description",
        ("estimated_budget_min", "estimated_budget_max", "currency"),
    ]


class LeadActivityInline(TabularInline):
    model = LeadActivity
    extra = 1
    tab = True
    fields = ["activity_type", "description", "performed_by", "created_at"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["performed_by"]
    ordering = ["-created_at"]


# ──────────────────────────────────────────────────────────────────────────────
# LEAD
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(Lead)
class LeadAdmin(ModelAdmin):
    list_display = [
        "display_header",
        "display_lead_type",
        "display_status",
        "company",
        "score",
        "assigned_to",
        "is_spam",
        "created_at",
    ]
    list_filter = [
        ("lead_type", ChoicesDropdownFilter),
        ("status", ChoicesDropdownFilter),
        ("assigned_to", RelatedDropdownFilter),
        "is_spam",
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["full_name", "email", "company", "phone"]
    autocomplete_fields = ["service_interest", "industry", "assigned_to"]
    readonly_fields = ["id", "created_at", "updated_at", "converted_at"]
    inlines = [QuoteRequestDetailInline, LeadActivityInline]
    date_hierarchy = "created_at"
    list_filter_submit = True
    compressed_fields = True
    actions = [
        "action_assign_to_me",
        "action_mark_contacted",
        "action_mark_qualified",
        "action_mark_won",
        "action_mark_lost",
        "action_mark_spam",
        "action_unmark_spam",
    ]

    fieldsets = (
        (
            _("Contact"),
            {
                "fields": ("id", "full_name", "email", "phone", "company", "job_title", "message"),
                "classes": ["tab"],
            },
        ),
        (
            _("Classification"),
            {
                "fields": (
                    "lead_type",
                    "status",
                    "service_interest",
                    "industry",
                    "budget_range",
                    "timeline",
                    "score",
                    "is_spam",
                    "assigned_to",
                    "lost_reason",
                    "converted_at",
                ),
                "classes": ["tab"],
            },
        ),
        (
            _("Attribution"),
            {
                "fields": (
                    "source_page",
                    "referrer_url",
                    ("utm_source", "utm_medium", "utm_campaign"),
                    ("utm_term", "utm_content"),
                    "ip_address",
                    "user_agent",
                    "country",
                    "language",
                ),
                "classes": ["tab", "collapse"],
            },
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )

    @display(description=_("Lead"), header=True)
    def display_header(self, obj):
        return [obj.full_name, obj.email, _initials(obj.full_name)]

    @display(
        description=_("Type"),
        label={
            "contact": "info",
            "quote": "warning",
            "consultation": "success",
            "newsletter": "info",
            "ai_assistant": "warning",
            "career": "info",
        },
    )
    def display_lead_type(self, obj):
        return obj.lead_type

    @display(
        description=_("Status"),
        label={
            "new": "info",
            "contacted": "warning",
            "qualified": "warning",
            "proposal_sent": "warning",
            "negotiation": "warning",
            "won": "success",
            "lost": "danger",
            "spam": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status

    @admin.action(description=_("Assign to me"))
    def action_assign_to_me(self, request, queryset):
        updated = queryset.update(assigned_to=request.user)
        self.message_user(request, _("%(count)d lead(s) assigned to you.") % {"count": updated})

    @admin.action(description=_("Mark as contacted"))
    def action_mark_contacted(self, request, queryset):
        queryset.update(status=Lead.Status.CONTACTED)

    @admin.action(description=_("Mark as qualified"))
    def action_mark_qualified(self, request, queryset):
        queryset.update(status=Lead.Status.QUALIFIED)

    @admin.action(description=_("Mark as won"))
    def action_mark_won(self, request, queryset):
        queryset.update(status=Lead.Status.WON, converted_at=timezone.now())

    @admin.action(description=_("Mark as lost"))
    def action_mark_lost(self, request, queryset):
        queryset.update(status=Lead.Status.LOST)

    @admin.action(description=_("Mark as spam"))
    def action_mark_spam(self, request, queryset):
        queryset.update(is_spam=True, status=Lead.Status.SPAM)

    @admin.action(description=_("Unmark as spam"))
    def action_unmark_spam(self, request, queryset):
        queryset.update(is_spam=False, status=Lead.Status.NEW)


# ──────────────────────────────────────────────────────────────────────────────
# NEWSLETTER SUBSCRIBER
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["email", "language", "display_active", "subscribed_at", "unsubscribed_at"]
    list_filter = ["is_active", "language"]
    search_fields = ["email"]
    readonly_fields = ["id", "subscribed_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["-subscribed_at"]


# ──────────────────────────────────────────────────────────────────────────────
# AVAILABILITY SLOT
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["get_weekday_display", "start_time", "end_time", "timezone", "max_bookings", "display_active"]
    list_filter = ["weekday", "is_active"]
    search_fields = ["timezone"]
    readonly_fields = ["id"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["weekday", "start_time"]

    @admin.display(description=_("Weekday"))
    def get_weekday_display(self, obj):
        return obj.get_weekday_display()


# ──────────────────────────────────────────────────────────────────────────────
# CONSULTATION BOOKING
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(ConsultationBooking)
class ConsultationBookingAdmin(ModelAdmin):
    list_display = [
        "lead",
        "scheduled_date",
        "scheduled_time",
        "meeting_type",
        "display_status",
        "calendar_provider",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("meeting_type", ChoicesDropdownFilter),
        ("scheduled_date", RangeDateFilter),
    ]
    search_fields = ["lead__full_name", "lead__email"]
    autocomplete_fields = ["lead", "slot"]
    readonly_fields = ["id", "created_at", "updated_at", "confirmed_at", "cancelled_at", "completed_at"]
    date_hierarchy = "scheduled_date"
    list_filter_submit = True
    actions = ["action_confirm", "action_cancel", "action_complete", "action_mark_no_show"]

    fieldsets = (
        (
            _("Booking"),
            {
                "fields": (
                    "id",
                    "lead",
                    "slot",
                    "scheduled_date",
                    "scheduled_time",
                    "timezone",
                    "meeting_type",
                    "status",
                ),
                "classes": ["tab"],
            },
        ),
        (
            _("Calendar Integration"),
            {"fields": ("calendar_provider", "calendar_event_id", "calendar_event_link"), "classes": ["tab"]},
        ),
        (_("Notes"), {"fields": ("notes", "cancellation_reason"), "classes": ["tab"]}),
        (
            _("Lifecycle"),
            {
                "fields": ("confirmed_at", "cancelled_at", "completed_at", "created_at", "updated_at"),
                "classes": ["tab"],
            },
        ),
    )

    @display(
        description=_("Status"),
        label={
            "pending": "warning",
            "confirmed": "success",
            "rescheduled": "info",
            "completed": "success",
            "cancelled": "danger",
            "no_show": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status

    @admin.action(description=_("Confirm selected bookings"))
    def action_confirm(self, request, queryset):
        queryset.update(status=ConsultationBooking.Status.CONFIRMED, confirmed_at=timezone.now())

    @admin.action(description=_("Cancel selected bookings"))
    def action_cancel(self, request, queryset):
        queryset.update(status=ConsultationBooking.Status.CANCELLED, cancelled_at=timezone.now())

    @admin.action(description=_("Mark as completed"))
    def action_complete(self, request, queryset):
        queryset.update(status=ConsultationBooking.Status.COMPLETED, completed_at=timezone.now())

    @admin.action(description=_("Mark as no-show"))
    def action_mark_no_show(self, request, queryset):
        queryset.update(status=ConsultationBooking.Status.NO_SHOW)


# ──────────────────────────────────────────────────────────────────────────────
# COST CALCULATOR
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(CostCalculatorRule)
class CostCalculatorRuleAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = [
        "service",
        "complexity_tier",
        "base_price_min",
        "base_price_max",
        "currency",
        "display_active",
    ]
    list_filter = [("service", RelatedDropdownFilter), ("complexity_tier", ChoicesDropdownFilter), "is_active"]
    search_fields = ["service__translations__name"]
    autocomplete_fields = ["service"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    list_filter_submit = True


@admin.register(CalculatorSubmission)
class CalculatorSubmissionAdmin(ModelAdmin):
    list_display = [
        "selected_service",
        "complexity_tier",
        "estimated_price_min",
        "estimated_price_max",
        "currency",
        "lead",
        "created_at",
    ]
    list_filter = [("complexity_tier", ChoicesDropdownFilter), ("created_at", RangeDateFilter)]
    search_fields = ["selected_service__translations__name", "lead__email"]
    autocomplete_fields = ["lead", "selected_service"]
    readonly_fields = [
        "id",
        "lead",
        "selected_service",
        "complexity_tier",
        "selected_features",
        "estimated_price_min",
        "estimated_price_max",
        "currency",
        "ip_address",
        "created_at",
    ]
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False