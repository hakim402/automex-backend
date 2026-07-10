"""
config/settings_unfold_additions.py
─────────────────────────────────────
"""

# ──────────────────────────────────────────────────────────────────────────────
# 4. UNFOLD dict — additions to your existing UNFOLD = {...} block.
#    Keep your existing SITE_TITLE / SITE_HEADER / SITE_LOGO / STYLES keys —
#    just merge these extra keys in alongside them.
# ──────────────────────────────────────────────────────────────────────────────

from django.templatetags.static import static  # noqa: E402
from django.urls import reverse_lazy  # noqa: E402
from django.utils.translation import gettext_lazy as _  # noqa: E402

UNFOLD_ADDITIONS = {
    # Feeds KPI cards + charts on the admin homepage (see dashboard.py)
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

    # Custom sidebar navigation grouping the accounts app logically instead
    # of relying on the default alphabetical model list.
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
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
        ],
    },
}
