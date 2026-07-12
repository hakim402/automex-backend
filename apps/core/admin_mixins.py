"""
apps/core/admin_mixins.py
──────────────────────────
Shared Unfold admin building blocks reused by apps.content / apps.crm /
apps.notifications / apps.assistant admin registrations, so every
PublishableModel-based content type (Service, CaseStudy, BlogPost) gets
identical status badges + editorial workflow actions without repeating
the same code four times.
"""
from __future__ import annotations

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from unfold.decorators import display


class PublishableAdminMixin:
    """
    Mix into any ModelAdmin registered for a model inheriting
    apps.core.models.PublishableModel (Service, CaseStudy, BlogPost, ...).

    Provides:
      - display_status()   — colored badge column for `status`
      - editorial_fieldset  — ready-made ("Editorial Workflow", {...}) tuple
                               to drop into `fieldsets`
      - bulk actions: submit for review / approve / reject / publish / archive

    Usage:
        class ServiceAdmin(TranslatableAdmin, PublishableAdminMixin, ModelAdmin):
            list_display = ["name", "display_status", ...]
            actions = [*PublishableAdminMixin.publishable_actions]
            fieldsets = (
                (...),
                PublishableAdminMixin.editorial_fieldset,
            )
    """

    publishable_actions = [
        "action_submit_for_review",
        "action_approve",
        "action_reject",
        "action_publish",
        "action_archive",
    ]

    editorial_readonly_fields = [
        "submitted_at",
        "reviewed_at",
        "approved_at",
        "published_at",
        "version",
    ]

    editorial_fieldset = (
        _("Editorial Workflow"),
        {
            "fields": (
                "status",
                ("submitted_by", "submitted_at"),
                ("reviewed_by", "reviewed_at"),
                "rejection_reason",
                ("approved_by", "approved_at"),
                "published_at",
                "version",
            ),
            "classes": ["tab"],
        },
    )

    @display(
        description=_("Status"),
        label={
            "draft": "info",
            "in_review": "warning",
            "approved": "success",
            "published": "success",
            "rejected": "danger",
            "archived": "info",
        },
    )
    def display_status(self, obj):
        return obj.status

    @admin.action(description=_("Submit for review"))
    def action_submit_for_review(self, request, queryset):
        updated = queryset.filter(status="draft").update(
            status="in_review", submitted_by=request.user, submitted_at=timezone.now()
        )
        self.message_user(
            request, _("%(count)d item(s) submitted for review.") % {"count": updated}
        )

    @admin.action(description=_("Approve selected"))
    def action_approve(self, request, queryset):
        updated = queryset.exclude(status="published").update(
            status="approved",
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
            approved_by=request.user,
            approved_at=timezone.now(),
        )
        self.message_user(
            request, _("%(count)d item(s) approved.") % {"count": updated}, messages.SUCCESS
        )

    @admin.action(description=_("Reject selected (back to draft)"))
    def action_reject(self, request, queryset):
        updated = queryset.update(
            status="rejected", reviewed_by=request.user, reviewed_at=timezone.now()
        )
        self.message_user(
            request, _("%(count)d item(s) rejected.") % {"count": updated}, messages.WARNING
        )

    @admin.action(description=_("Publish selected"))
    def action_publish(self, request, queryset):
        updated = queryset.update(status="published", published_at=timezone.now())
        self.message_user(
            request, _("%(count)d item(s) published.") % {"count": updated}, messages.SUCCESS
        )

    @admin.action(description=_("Archive selected"))
    def action_archive(self, request, queryset):
        updated = queryset.update(status="archived")
        self.message_user(
            request, _("%(count)d item(s) archived.") % {"count": updated}, messages.WARNING
        )


class ActiveToggleAdminMixin:
    """Mix into any ModelAdmin for a model with a plain `is_active` BooleanField."""

    @display(description=_("Active"), boolean=True)
    def display_active(self, obj):
        return obj.is_active

    @admin.action(description=_("Activate selected"))
    def action_activate(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request, _("%(count)d item(s) activated.") % {"count": updated}, messages.SUCCESS
        )

    @admin.action(description=_("Deactivate selected"))
    def action_deactivate(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request, _("%(count)d item(s) deactivated.") % {"count": updated}, messages.WARNING
        )