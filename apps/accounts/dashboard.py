"""
apps/accounts/dashboard.py
───────────────────────────
Feeds the custom Unfold admin homepage (templates/admin/index.html)
with KPI cards + chart data.

Wire it up in settings.py:

    UNFOLD = {
        ...
        "DASHBOARD_CALLBACK": "apps.accounts.dashboard.dashboard_callback",
    }
"""

from __future__ import annotations

import json
from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpRequest
from django.utils import timezone

from .models import Tenant, User, UserRefreshToken


def dashboard_callback(request: HttpRequest, context: dict) -> dict:
    now = timezone.now()

    users_qs = User.objects.filter(deleted_at__isnull=True)
    total_users = users_qs.count()
    active_users = users_qs.filter(is_active=True).count()
    verified_users = users_qs.filter(is_email_verified=True).count()
    locked_users = users_qs.filter(locked_until__gt=now).count()

    total_tenants = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(is_active=True).count()

    active_sessions = UserRefreshToken.objects.filter(
        revoked=False, expires_at__gt=now
    ).count()

    # ── Role breakdown (for a doughnut chart) ────────────────────────────
    role_breakdown = list(
        users_qs.values("role").annotate(count=Count("id")).order_by("role")
    )
    role_labels = [str(User.Role(row["role"]).label) for row in role_breakdown]
    role_data = [row["count"] for row in role_breakdown]

    # ── Signups over the last 14 days (for a line chart) ─────────────────
    window_start = now - timedelta(days=13)
    daily_signups = (
        users_qs.filter(created_at__gte=window_start)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    signup_by_day = {row["day"]: row["count"] for row in daily_signups}
    signup_labels = []
    signup_data = []
    for i in range(14):
        day = (window_start + timedelta(days=i)).date()
        signup_labels.append(day.strftime("%b %d"))
        signup_data.append(signup_by_day.get(day, 0))

    # ── Tenant tier breakdown table ───────────────────────────────────────
    tenant_tiers = list(
        Tenant.objects.values("subscription_tier")
        .annotate(count=Count("id"))
        .order_by("subscription_tier")
    )

    context.update(
        {
            "kpi_cards": [
                {
                    "title": "Total Users",
                    "metric": total_users,
                    "footer": f"{active_users} active",
                },
                {
                    "title": "Verified Emails",
                    "metric": verified_users,
                    "footer": f"{total_users - verified_users} pending",
                },
                {
                    "title": "Locked Accounts",
                    "metric": locked_users,
                    "footer": "requires attention" if locked_users else "all clear",
                },
                {
                    "title": "Active Sessions",
                    "metric": active_sessions,
                    "footer": "live refresh tokens",
                },
                {
                    "title": "Tenants",
                    "metric": total_tenants,
                    "footer": f"{active_tenants} active",
                },
            ],
            "signup_chart_labels": json.dumps(signup_labels),
            "signup_chart_data": json.dumps(signup_data),
            "role_chart_labels": json.dumps(role_labels),
            "role_chart_data": json.dumps(role_data),
            "tenant_tiers": tenant_tiers,
        }
    )
    return context