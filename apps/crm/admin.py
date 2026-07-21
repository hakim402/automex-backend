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
    SupportTicket,
    SupportTicketMessage,
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
        ("quoted_price_min", "quoted_price_max", "quoted_currency"),
        "version",
        "admin_notes",
    ]


class LeadActivityInline(TabularInline):
    model = LeadActivity
    extra = 1
    tab = True
    fields = ["activity_type", "description", "message", "is_customer_visible", "performed_by", "created_at"]
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
        "display_priority",
        "company",
        "score",
        "assigned_to",
        "user",
        "is_spam",
        "created_at",
    ]
    list_filter = [
        ("lead_type", ChoicesDropdownFilter),
        ("status", ChoicesDropdownFilter),
        ("priority", ChoicesDropdownFilter),
        ("source_channel", ChoicesDropdownFilter),
        ("assigned_to", RelatedDropdownFilter),
        "is_spam",
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["full_name", "email", "company", "phone"]
    autocomplete_fields = ["service_interest", "industry", "assigned_to", "user"]
    readonly_fields = ["id", "guest_token", "created_at", "updated_at", "converted_at"]
    inlines = [QuoteRequestDetailInline, LeadActivityInline]
    date_hierarchy = "created_at"
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True
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
                "description": _(
                    "Basic contact information collected from the lead capture form. "
                    "The message field contains the original inquiry text typed by the prospect."
                ),
            },
        ),
        (
            _("Classification"),
            {
                "fields": (
                    "lead_type",
                    "status",
                    "priority",
                    "service_interest",
                    "industry",
                    "budget_range",
                    "timeline",
                    "score",
                    "is_spam",
                    "assigned_to",
                    "lost_reason",
                    "converted_at",
                    "expected_close_date",
                ),
                "classes": ["tab"],
                "description": _(
                    "Categorize and prioritize the lead. Score is auto-calculated based on "
                    "engagement signals (higher = hotter). Priority helps the sales team triage. "
                    "Mark as spam to hide from active pipelines. Lost reason should be filled in "
                    "when status is 'lost'."
                ),
            },
        ),
        (
            _("User & Tracking"),
            {
                "fields": ("user", "guest_token", "tags", "source_channel"),
                "classes": ["tab"],
                "description": _(
                    "If the lead is linked to a registered user account, the User field is set. "
                    "Guest token identifies anonymous visitors across sessions. "
                    "Source channel records how the lead first arrived (website, LinkedIn, referral, etc.)."
                ),
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
                "description": _(
                    "Marketing attribution data captured automatically from the lead's browser. "
                    "UTM parameters track campaign performance in analytics. "
                    "Source page is the exact URL the lead was on when they submitted the form. "
                    "IP and user-agent are used for geo-location and device analytics."
                ),
            },
        ),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ["tab"], "description": _("Auto-managed timestamps.")},
        ),
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

    @display(
        description=_("Priority"),
        label={"low": "info", "normal": "info", "high": "warning", "urgent": "danger"},
    )
    def display_priority(self, obj):
        return obj.priority

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
    list_filter_submit = True
    warn_unsaved_form = True


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
    list_filter_submit = True
    warn_unsaved_form = True

    fieldsets = (
        (
            _("Slot"),
            {
                "fields": ("id", "weekday", "start_time", "end_time", "timezone", "max_bookings"),
                "classes": ["tab"],
                "description": _(
                    "Define a recurring weekly availability window. "
                    "Max bookings limits how many consultations can be booked into this slot per day. "
                    "Timezone is used to display the slot time correctly to the lead."
                ),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active",),
                "classes": ["tab"],
                "description": _("Inactive slots are hidden from the booking calendar."),
            },
        ),
    )

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
        "user",
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
    autocomplete_fields = ["lead", "slot", "user"]
    readonly_fields = ["id", "created_at", "updated_at", "confirmed_at", "cancelled_at", "completed_at"]
    date_hierarchy = "scheduled_date"
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True
    actions = ["action_confirm", "action_cancel", "action_complete", "action_mark_no_show"]

    fieldsets = (
        (
            _("Booking"),
            {
                "fields": (
                    "id",
                    "lead",
                    "user",
                    "slot",
                    "scheduled_date",
                    "scheduled_time",
                    "timezone",
                    "meeting_type",
                    "meeting_link",
                    "status",
                ),
                "classes": ["tab"],
                "description": _(
                    "Core booking details. The slot links to a pre-configured availability window. "
                    "Meeting link is auto-generated for online meetings or manually entered for in-person. "
                    "Status tracks the lifecycle: pending → confirmed → completed / cancelled."
                ),
            },
        ),
        (
            _("Reschedule"),
            {"fields": ("reschedule_count", "rescheduled_from"), "classes": ["tab", "collapse"],
             "description": _("Tracks how many times this booking was rescheduled and the previous booking it came from.")},
        ),
        (
            _("Calendar Integration"),
            {"fields": ("calendar_provider", "calendar_event_id", "calendar_event_link"), "classes": ["tab"],
             "description": _(
                 "When connected to Google Calendar / Outlook, the provider, event ID and link "
                 "are populated automatically after the event is synced."
             )},
        ),
        (
            _("Notes"),
            {"fields": ("notes", "cancellation_reason"), "classes": ["tab"],
            "description": _("Internal notes are visible to admins only. Cancellation reason is shown when status is 'cancelled'.")},
        ),
        (
            _("Lifecycle"),
            {
                "fields": ("reminder_sent_at", "confirmed_at", "cancelled_at", "completed_at", "created_at", "updated_at"),
                "classes": ["tab"],
                "description": _("Auto-populated timestamps for each booking state transition."),
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
    warn_unsaved_form = True


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


# ──────────────────────────────────────────────────────────────────────────────
# SUPPORT TICKETS
# ──────────────────────────────────────────────────────────────────────────────


class SupportTicketMessageInline(TabularInline):
    model = SupportTicketMessage
    extra = 0
    tab = True
    fields = ["author_name", "author_is_staff", "body", "is_read", "created_at"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["author_user"]
    ordering = ["-created_at"]


@admin.register(SupportTicket)
class SupportTicketAdmin(ModelAdmin):
    list_display = [
        "title",
        "display_ticket_type",
        "display_status",
        "display_priority",
        "assigned_to",
        "user",
        "guest_email",
        "created_at",
    ]
    list_filter = [
        ("ticket_type", ChoicesDropdownFilter),
        ("status", ChoicesDropdownFilter),
        ("priority", ChoicesDropdownFilter),
        ("assigned_to", RelatedDropdownFilter),
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["title", "description", "guest_email", "user__email"]
    autocomplete_fields = ["user", "assigned_to", "related_lead", "related_service"]
    readonly_fields = ["id", "slug", "guest_token", "resolved_at", "closed_at", "created_at", "updated_at"]
    inlines = [SupportTicketMessageInline]
    date_hierarchy = "created_at"
    list_filter_submit = True
    compressed_fields = True
    warn_unsaved_form = True
    save_on_top = True
    actions = ["action_mark_in_progress", "action_mark_resolved", "action_mark_closed"]

    fieldsets = (
        (
            _("Ticket"),
            {
                "fields": (
                    "id",
                    "title",
                    "slug",
                    "description",
                    "ticket_type",
                    "status",
                    "priority",
                ),
                "classes": ["tab"],
                "description": _(
                    "Core ticket information. Slug is auto-generated from the title. "
                    "Status reflects the current lifecycle stage. Priority helps the support team triage."
                ),
            },
        ),
        (
            _("Ownership"),
            {"fields": ("user", "guest_email", "guest_token", "assigned_to"), "classes": ["tab"],
             "description": _("Who submitted the ticket (registered user or guest) and who is handling it.")},
        ),
        (
            _("Relations"),
            {"fields": ("related_lead", "related_service"), "classes": ["tab", "collapse"],
             "description": _("Link this ticket to a related lead or service to provide support context.")},
        ),
        (
            _("Resolution"),
            {"fields": ("resolution_summary", "resolved_at", "closed_at"), "classes": ["tab"],
             "description": _(
                 "Resolution summary should describe how the issue was solved. "
                 "Resolved-at and closed-at are auto-populated when marking status transitions."
             )},
        ),
        (
            _("Audit"),
            {"fields": ("created_at", "updated_at"), "classes": ["tab"],
            "description": _("Auto-managed timestamps.")},
        ),
    )

    @display(description=_("Type"))
    def display_ticket_type(self, obj):
        return obj.ticket_type

    @display(
        description=_("Status"),
        label={
            "open": "info",
            "in_progress": "warning",
            "waiting_customer": "warning",
            "waiting_admin": "warning",
            "resolved": "success",
            "closed": "danger",
        },
    )
    def display_status(self, obj):
        return obj.status

    @display(
        description=_("Priority"),
        label={"low": "info", "normal": "info", "high": "warning", "urgent": "danger"},
    )
    def display_priority(self, obj):
        return obj.priority

    @admin.action(description=_("Mark as in progress"))
    def action_mark_in_progress(self, request, queryset):
        queryset.update(status=SupportTicket.Status.IN_PROGRESS)

    @admin.action(description=_("Mark as resolved"))
    def action_mark_resolved(self, request, queryset):
        queryset.update(status=SupportTicket.Status.RESOLVED, resolved_at=timezone.now())

    @admin.action(description=_("Mark as closed"))
    def action_mark_closed(self, request, queryset):
        queryset.update(status=SupportTicket.Status.CLOSED, closed_at=timezone.now())


@admin.register(SupportTicketMessage)
class SupportTicketMessageAdmin(ModelAdmin):
    list_display = ["ticket", "author_name", "author_is_staff", "is_read", "created_at"]
    list_filter = ["author_is_staff", "is_read"]
    search_fields = ["ticket__title", "author_name", "body"]
    autocomplete_fields = ["ticket", "author_user"]
    readonly_fields = ["id", "created_at", "updated_at"]
    list_filter_submit = True
    warn_unsaved_form = True


# ──────────────────────────────────────────────────────────────────────────────
# LEAD ACTIVITY (standalone — global timeline; also inlined in LeadAdmin)
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(LeadActivity)
class LeadActivityAdmin(ModelAdmin):
    list_display = ["lead", "display_activity_type", "description", "performed_by", "is_customer_visible", "created_at"]
    list_filter = [
        ("activity_type", ChoicesDropdownFilter),
        "is_customer_visible",
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["description", "message", "lead__full_name", "lead__email"]
    autocomplete_fields = ["lead", "performed_by", "attachment"]
    readonly_fields = ["id", "created_at", "updated_at"]
    date_hierarchy = "created_at"
    list_filter_submit = True

    fieldsets = (
        (
            _("Activity"),
            {
                "fields": ("id", "lead", "activity_type", "description"),
                "classes": ["tab"],
                "description": _(
                    "Activity type classifies what happened (call, email, meeting, note, etc.). "
                    "Description is a short internal summary shown in the lead timeline."
                ),
            },
        ),
        (
            _("Message"),
            {
                "fields": ("message", "is_customer_visible", "attachment"),
                "classes": ["tab"],
                "description": _(
                    "Customer-visible activities appear in the client dashboard. "
                    "Use this for status updates and messages the client should see."
                ),
            },
        ),
        (
            _("Audit"),
            {
                "fields": ("performed_by", "created_at", "updated_at"),
                "classes": ["tab"],
                "description": _("Who performed this activity and when."),
            },
        ),
    )

    @display(
        description=_("Type"),
        label={
            "status_change": "warning",
            "note": "info",
            "email_sent": "success",
            "call": "info",
            "meeting": "success",
            "assigned": "warning",
            "other": "info",
        },
    )
    def display_activity_type(self, obj):
        return obj.activity_type