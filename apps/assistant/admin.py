"""
apps/assistant/admin.py
────────────────────────
Unfold admin registrations for the AI Sales Assistant: AIConversation
(+ read-only AIMessage inline showing the transcript) and AIKnowledgeEntry
(the curated Q&A knowledge base used to ground the assistant's answers).
"""
from __future__ import annotations

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter, RangeDateFilter, RelatedDropdownFilter
from unfold.decorators import display

from apps.core.admin_mixins import ActiveToggleAdminMixin

from .models import AIConversation, AIKnowledgeEntry, AIMessage

ROLE_LABELS = {"user": "info", "assistant": "success", "system": "warning"}


# ──────────────────────────────────────────────────────────────────────────────
# CONVERSATION  (+ read-only message transcript inline)
# ──────────────────────────────────────────────────────────────────────────────


class AIMessageInline(TabularInline):
    model = AIMessage
    extra = 0
    tab = True
    can_delete = False
    fields = ["role", "content", "detected_intent", "tokens_used", "created_at"]
    readonly_fields = fields
    ordering = ["created_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AIConversation)
class AIConversationAdmin(ModelAdmin):
    list_display = [
        "session_id",
        "channel",
        "language",
        "lead",
        "display_lead_captured",
        "display_active",
        "started_at",
    ]
    list_filter = [
        ("channel", ChoicesDropdownFilter),
        "language",
        "lead_captured",
        "is_active",
        ("started_at", RangeDateFilter),
    ]
    search_fields = ["session_id", "lead__email", "lead__full_name"]
    autocomplete_fields = ["lead"]
    readonly_fields = ["id", "session_id", "started_at", "ended_at", "ip_address", "user_agent", "metadata"]
    inlines = [AIMessageInline]
    date_hierarchy = "started_at"
    list_filter_submit = True
    actions = ["action_close_conversation"]

    fieldsets = (
        (
            _("Conversation"),
            {"fields": ("id", "session_id", "channel", "language", "lead", "lead_captured"), "classes": ["tab"]},
        ),
        (_("Context"), {"fields": ("page_url", "ip_address", "user_agent", "metadata"), "classes": ["tab"]}),
        (_("Lifecycle"), {"fields": ("is_active", "started_at", "ended_at"), "classes": ["tab"]}),
    )

    @display(description=_("Lead Captured"), boolean=True)
    def display_lead_captured(self, obj):
        return obj.lead_captured

    @display(description=_("Active"), boolean=True)
    def display_active(self, obj):
        return obj.is_active

    @admin.action(description=_("Close selected conversations"))
    def action_close_conversation(self, request, queryset):
        updated = queryset.filter(is_active=True).update(is_active=False, ended_at=timezone.now())
        self.message_user(request, _("%(count)d conversation(s) closed.") % {"count": updated})


# ──────────────────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE
# ──────────────────────────────────────────────────────────────────────────────


@admin.register(AIKnowledgeEntry)
class AIKnowledgeEntryAdmin(ActiveToggleAdminMixin, ModelAdmin):
    list_display = ["question", "category", "related_service", "display_active"]
    list_filter = ["category", ("related_service", RelatedDropdownFilter), "is_active"]
    search_fields = ["question", "answer", "category"]
    autocomplete_fields = ["related_service"]
    readonly_fields = ["id", "created_at", "updated_at"]
    actions = ["action_activate", "action_deactivate"]
    ordering = ["category", "question"]
    list_filter_submit = True

    fieldsets = (
        (_("Q&A"), {"fields": ("id", "question", "answer", "category"), "classes": ["tab"]}),
        (_("Linking"), {"fields": ("related_service", "is_active"), "classes": ["tab"]}),
        (_("Audit"), {"fields": ("created_at", "updated_at"), "classes": ["tab"]}),
    )