"""
apps/content/models/team.py
───────────────────────────────
Team member profiles for the expertise/"Meet the Team" section.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from parler.models import TranslatableModel, TranslatedFields

from apps.core.models import OrderableModel, TimeStampedModel, UUIDModel


class TeamMember(TranslatableModel, UUIDModel, TimeStampedModel, OrderableModel):
    class Department(models.TextChoices):
        ENGINEERING = "engineering", _("Engineering")
        DESIGN      = "design",      _("Design")
        AI          = "ai",          _("AI")
        DEVOPS      = "devops",      _("DevOps")
        MANAGEMENT  = "management",  _("Management")
        SALES       = "sales",       _("Sales")
        QA          = "qa",          _("QA")
        OTHER       = "other",       _("Other")

    # Optional link to a staff login for team members who also have
    # dashboard access; public-only profiles leave this blank.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="team_profile", verbose_name=_("linked user account"),
    )

    translations = TranslatedFields(
        full_name  = models.CharField(_("full name"), max_length=200),
        role_title = models.CharField(_("role title"), max_length=200),
        bio        = models.TextField(_("bio"), blank=True),
    )
    slug       = models.SlugField(_("slug"), max_length=220, unique=True)
    department = models.CharField(
        _("department"), max_length=20, choices=Department.choices, default=Department.OTHER,
    )
    photo = models.ForeignKey(
        "core.MediaAsset",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+", verbose_name=_("photo"),
    )

    email        = models.EmailField(_("public email"), blank=True)
    linkedin_url = models.URLField(_("LinkedIn URL"), blank=True)
    github_url   = models.URLField(_("GitHub URL"), blank=True)
    twitter_url  = models.URLField(_("Twitter/X URL"), blank=True)

    is_leadership = models.BooleanField(_("leadership"), default=False)
    is_active     = models.BooleanField(_("active"), default=True, db_index=True)

    # ── Enterprise fields ──────────────────────────────────────────
    specializations = models.JSONField(
        _("specializations"), default=list, blank=True,
        help_text=_('List of specialization areas, e.g. ["NLP", "MLOps"]'),
    )
    certifications = models.JSONField(
        _("certifications"), default=list, blank=True,
        help_text=_('List of certifications, e.g. ["AWS Solutions Architect", "Google Cloud Professional"]'),
    )
    years_of_experience = models.PositiveIntegerField(
        _("years of experience"), null=True, blank=True,
    )
    education = models.JSONField(
        _("education"), default=list, blank=True,
        help_text=_('List of education entries, e.g. [{"degree": "MSc", "institution": "MIT", "year": 2015}].'),
    )
    languages = models.JSONField(
        _("languages"), default=list, blank=True,
        help_text=_('List of spoken languages, e.g. ["English", "Spanish"]'),
    )
    is_available_for_consulting = models.BooleanField(
        _("available for consulting"), default=False, db_index=True,
    )
    projects_showcase = models.ManyToManyField(
        "content.CaseStudy", blank=True,
        related_name="team_members", verbose_name=_('projects showcase'),
    )

    class Meta:
        ordering            = ["order"]
        verbose_name        = _("team member")
        verbose_name_plural = _("team members")

    def __str__(self) -> str:
        name = self.safe_translation_getter("full_name", any_language=True) or self.slug
        role = self.safe_translation_getter("role_title", any_language=True) or ""
        return f"{name} ({role})" if role else name
