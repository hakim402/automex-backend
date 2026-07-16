"""
config/settings_unfold_additions.py
─────────────────────────────────────
Defines UNFOLD_ADDITIONS, merged into the UNFOLD dict in settings.py:

    from config.settings_unfold_additions import UNFOLD_ADDITIONS
    ...
    UNFOLD = {
        ...your existing keys (SITE_TITLE, SITE_LOGO, STYLES, etc.)...
        **UNFOLD_ADDITIONS,
    }

Covers every model registered across all 6 apps (accounts, core, content,
crm, notifications, assistant) so the curated sidebar is complete —
`SIDEBAR["show_all_applications"] = False` means anything NOT listed here
is admin-reachable by direct URL but won't appear in the nav.
"""

from django.urls import reverse_lazy  # noqa: E402
from django.utils.translation import gettext_lazy as _  # noqa: E402

UNFOLD_ADDITIONS = {
    # Feeds KPI cards + charts on the admin homepage.
    # See apps/accounts/dashboard.py::dashboard_callback
    "DASHBOARD_CALLBACK": "apps.accounts.dashboard.dashboard_callback",

    # Modern indigo/violet enterprise palette (Tailwind color scale).
    # Optional — remove this key to keep Unfold's default palette.
    "COLORS": {
        "primary": {
            "50": "238 242 255",
            "100": "224 231 255",
            "200": "199 210 254",
            "300": "165 180 252",
            "400": "129 140 248",
            "500": "99 102 241",
            "600": "79 70 229",
            "700": "67 56 202",
            "800": "55 48 163",
            "900": "49 46 129",
        },
    },

    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            # ── Overview ──────────────────────────────────────────────
            {
                "title": _("Overview"),
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            # ── Identity & Access (apps.accounts) ────────────────────
            {
                "title": _("Identity & Access"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                    {
                        "title": _("Tenants"),
                        "icon": "domain",
                        "link": reverse_lazy("admin:accounts_tenant_changelist"),
                    },
                    {
                        "title": _("Roles"),
                        "icon": "shield_person",
                        "link": reverse_lazy("admin:accounts_role_changelist"),
                    },
                    {
                        "title": _("Permissions"),
                        "icon": "key",
                        "link": reverse_lazy("admin:accounts_permission_changelist"),
                    },
                    {
                        "title": _("Role Assignments"),
                        "icon": "assignment_ind",
                        "link": reverse_lazy("admin:accounts_userroleassignment_changelist"),
                    },
                ],
            },
            # ── Security (apps.accounts) ─────────────────────────────
            {
                "title": _("Security"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Active Sessions"),
                        "icon": "devices",
                        "link": reverse_lazy("admin:accounts_userrefreshtoken_changelist"),
                    },
                    {
                        "title": _("MFA"),
                        "icon": "verified_user",
                        "link": reverse_lazy("admin:accounts_usermfa_changelist"),
                    },
                    {
                        "title": _("Magic Links"),
                        "icon": "link",
                        "link": reverse_lazy("admin:accounts_magiclinktoken_changelist"),
                    },
                    {
                        "title": _("Email Verifications"),
                        "icon": "mark_email_read",
                        "link": reverse_lazy("admin:accounts_emailverificationtoken_changelist"),
                    },
                    {
                        "title": _("Password Resets"),
                        "icon": "lock_reset",
                        "link": reverse_lazy("admin:accounts_passwordresettoken_changelist"),
                    },
                ],
            },
            # ── Content Library (apps.core) ──────────────────────────
            {
                "title": _("Content Library"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Media Assets"),
                        "icon": "perm_media",
                        "link": reverse_lazy("admin:core_mediaasset_changelist"),
                    },
                    {
                        "title": _("Content Revisions"),
                        "icon": "history",
                        "link": reverse_lazy("admin:core_contentrevision_changelist"),
                    },
                    {
                        "title": _("SEO Settings"),
                        "icon": "search",
                        "link": reverse_lazy("admin:core_seosettings_changelist"),
                    },
                    {
                        "title": _("Redirects"),
                        "icon": "alt_route",
                        "link": reverse_lazy("admin:core_redirect_changelist"),
                    },
                ],
            },
            # ── Website Content (apps.content) ───────────────────────
            {
                "title": _("Website Content"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Services"),
                        "icon": "design_services",
                        "link": reverse_lazy("admin:content_service_changelist"),
                    },
                    {
                        "title": _("Service Categories"),
                        "icon": "category",
                        "link": reverse_lazy("admin:content_servicecategory_changelist"),
                    },
                    {
                        "title": _("Case Studies"),
                        "icon": "cases",
                        "link": reverse_lazy("admin:content_casestudy_changelist"),
                    },
                    {
                        "title": _("Blog Posts"),
                        "icon": "article",
                        "link": reverse_lazy("admin:content_blogpost_changelist"),
                    },
                    {
                        "title": _("Blog Categories"),
                        "icon": "topic",
                        "link": reverse_lazy("admin:content_blogcategory_changelist"),
                    },
                    {
                        "title": _("Blog Tags"),
                        "icon": "sell",
                        "link": reverse_lazy("admin:content_blogtag_changelist"),
                    },
                    {
                        "title": _("Team Members"),
                        "icon": "groups",
                        "link": reverse_lazy("admin:content_teammember_changelist"),
                    },
                    {
                        "title": _("Testimonials"),
                        "icon": "format_quote",
                        "link": reverse_lazy("admin:content_testimonial_changelist"),
                    },
                    {
                        "title": _("FAQs"),
                        "icon": "help",
                        "link": reverse_lazy("admin:content_faq_changelist"),
                    },
                    {
                        "title": _("Technologies"),
                        "icon": "code",
                        "link": reverse_lazy("admin:content_technology_changelist"),
                    },
                    {
                        "title": _("Industries"),
                        "icon": "factory",
                        "link": reverse_lazy("admin:content_industry_changelist"),
                    },
                    {
                        "title": _("Process Steps"),
                        "icon": "timeline",
                        "link": reverse_lazy("admin:content_processstep_changelist"),
                    },
                ],
            },
            # ── Sales & CRM (apps.crm) ────────────────────────────────
            {
                "title": _("Sales & CRM"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Leads"),
                        "icon": "person_search",
                        "link": reverse_lazy("admin:crm_lead_changelist"),
                    },
                    {
                        "title": _("Consultation Bookings"),
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:crm_consultationbooking_changelist"),
                    },
                    {
                        "title": _("Availability Slots"),
                        "icon": "event_available",
                        "link": reverse_lazy("admin:crm_availabilityslot_changelist"),
                    },
                    {
                        "title": _("Newsletter Subscribers"),
                        "icon": "mail",
                        "link": reverse_lazy("admin:crm_newslettersubscriber_changelist"),
                    },
                    {
                        "title": _("Cost Calculator Rules"),
                        "icon": "calculate",
                        "link": reverse_lazy("admin:crm_costcalculatorrule_changelist"),
                    },
                    {
                        "title": _("Calculator Submissions"),
                        "icon": "request_quote",
                        "link": reverse_lazy("admin:crm_calculatorsubmission_changelist"),
                    },
                ],
            },
            # ── Notifications (apps.notifications) ───────────────────
            {
                "title": _("Notifications"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Notifications"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                    {
                        "title": _("Templates"),
                        "icon": "description",
                        "link": reverse_lazy("admin:notifications_notificationtemplate_changelist"),
                    },
                    {
                        "title": _("Provider Configs"),
                        "icon": "settings_input_component",
                        "link": reverse_lazy("admin:notifications_notificationproviderconfig_changelist"),
                    },
                    {
                        "title": _("Preferences"),
                        "icon": "tune",
                        "link": reverse_lazy("admin:notifications_notificationpreference_changelist"),
                    },
                ],
            },
            # ── AI Assistant (apps.assistant) ─────────────────────────
            {
                "title": _("AI Assistant"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Conversations"),
                        "icon": "forum",
                        "link": reverse_lazy("admin:assistant_aiconversation_changelist"),
                    },
                    {
                        "title": _("Knowledge Base"),
                        "icon": "psychology",
                        "link": reverse_lazy("admin:assistant_aiknowledgeentry_changelist"),
                    },
                ],
            },
            # ── System (framework/infra models, kept out of the way) ─
            {
                "title": _("System"),
                "collapsible": True,
                "items": [
                    {
                        "title": _("Groups"),
                        "icon": "groups_2",
                        "link": reverse_lazy("admin:auth_group_changelist"),
                    },
                    {
                        "title": _("Periodic Tasks"),
                        "icon": "schedule",
                        "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist"),
                    },
                    {
                        "title": _("Outstanding Tokens"),
                        "icon": "token",
                        "link": reverse_lazy("admin:token_blacklist_outstandingtoken_changelist"),
                    },
                    {
                        "title": _("Blacklisted Tokens"),
                        "icon": "block",
                        "link": reverse_lazy("admin:token_blacklist_blacklistedtoken_changelist"),
                    },
                ],
            },
        ],
    },
}