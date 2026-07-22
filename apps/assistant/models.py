"""
apps/assistant/models.py
────────────────────────────
AI Sales Assistant. Per the agreed design: a lead-capturing conversational
bot (Groq-backed at the service layer; provider is swappable). Every
conversation is persisted; when the bot detects intent signals mid-chat,
a Lead (apps.crm.Lead, lead_type=AI_ASSISTANT) is created/linked without
interrupting the conversation.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields

from apps.core.models import TimeStampedModel, UUIDModel


class AIConversation(UUIDModel, TimeStampedModel):
    class Channel(models.TextChoices):
        WEBSITE_WIDGET = "website_widget", _("Website Widget")
        WHATSAPP       = "whatsapp",       _("WhatsApp")
        FACEBOOK       = "facebook",       _("Facebook Messenger")

    session_id = models.CharField(_("session id"), max_length=100, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_conversations", verbose_name=_("user"),
        help_text=_("Authenticated user, if the visitor was logged in."),
    )
    lead = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_conversations", verbose_name=_("captured lead"),
    )

    channel  = models.CharField(_("channel"), max_length=20, choices=Channel.choices, default=Channel.WEBSITE_WIDGET)
    language = models.CharField(_("language"), max_length=10, default="en")

    is_active     = models.BooleanField(_("active"), default=True, db_index=True)
    lead_captured = models.BooleanField(_("lead captured"), default=False)

    page_url   = models.CharField(_("page URL"), max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    user_agent = models.TextField(_("user agent"), blank=True)
    metadata   = models.JSONField(_("metadata"), default=dict, blank=True)

    started_at = models.DateTimeField(_("started at"), auto_now_add=True)
    ended_at   = models.DateTimeField(_("ended at"), null=True, blank=True)

    class Meta:
        ordering            = ["-started_at"]
        verbose_name        = _("AI conversation")
        verbose_name_plural = _("AI conversations")
        indexes = [
            models.Index(fields=["is_active", "-started_at"], name="idx_aiconv_active_started"),
            models.Index(fields=["user", "-started_at"], name="idx_aiconv_user_started"),
        ]

    def __str__(self) -> str:
        return f"Conversation {self.session_id}"


class AIMessage(UUIDModel):
    class Role(models.TextChoices):
        USER      = "user",      _("User")
        ASSISTANT = "assistant", _("Assistant")
        SYSTEM    = "system",    _("System")

    conversation = models.ForeignKey(
        AIConversation, on_delete=models.CASCADE, related_name="messages", verbose_name=_("conversation"),
    )
    role    = models.CharField(_("role"), max_length=10, choices=Role.choices)
    content = models.TextField(_("content"))

    tokens_used     = models.PositiveIntegerField(_("tokens used"), null=True, blank=True)
    detected_intent = models.CharField(_("detected intent"), max_length=100, blank=True)
    metadata        = models.JSONField(_("metadata"), default=dict, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        ordering            = ["created_at"]
        verbose_name        = _("AI message")
        verbose_name_plural = _("AI messages")
        indexes = [models.Index(fields=["conversation", "created_at"], name="idx_aimsg_conv_created")]

    def __str__(self) -> str:
        return f"{self.get_role_display()}: {self.content[:50]}"


class AIKnowledgeEntry(TranslatableModel, UUIDModel, TimeStampedModel):
    """Curated Q&A pairs used to ground the assistant's answers about AUTOMEX."""

    translations = TranslatedFields(
        question = models.CharField(_("question"), max_length=500),
        answer   = models.TextField(_("answer")),
    )
    category = models.CharField(_("category"), max_length=100, blank=True)

    related_service = models.ForeignKey(
        "content.Service",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ai_knowledge_entries", verbose_name=_("related service"),
    )
    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    class Meta:
        ordering            = ["category"]
        verbose_name        = _("AI knowledge entry")
        verbose_name_plural = _("AI knowledge entries")

    def __str__(self) -> str:
        return self.safe_translation_getter("question", any_language=True) or str(self.id)
