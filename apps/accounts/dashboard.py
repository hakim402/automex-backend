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

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpRequest
from django.utils import timezone

from apps.assistant.models import AIConversation
from apps.content.models import BlogPost, Service
from apps.crm.models import ConsultationBooking, Lead, SupportTicket
from apps.notifications.models import Notification

from .models import Tenant, User, UserRefreshToken


def get_site_symbol(request):
    """
    Returns a monogram/symbol for the Unfold sidebar header.
    Used as SITE_SYMBOL in UNFOLD settings.
    """
    return "◈"  # Geometric diamond — distinctive and professional


def dashboard_callback(request: HttpRequest, context: dict) -> dict:
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # ── Accounts ──────────────────────────────────────────────────────
    users_qs = User.objects.filter(deleted_at__isnull=True)
    total_users = users_qs.count()
    active_users = users_qs.filter(is_active=True).count()
    verified_users = users_qs.filter(is_email_verified=True).count()
    locked_users = users_qs.filter(locked_until__gt=now).count()
    new_users_this_week = users_qs.filter(created_at__gte=week_ago).count()
    unverified_users = total_users - verified_users

    total_tenants = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(is_active=True).count()
    enterprise_tenants = Tenant.objects.filter(subscription_tier=Tenant.SubscriptionTier.ENTERPRISE).count()

    active_sessions = UserRefreshToken.objects.filter(
        revoked=False, expires_at__gt=now
    ).count()

    # ── CRM ───────────────────────────────────────────────────────────
    total_leads = Lead.objects.count()
    open_leads = Lead.objects.filter(status__in=["new", "contacted", "qualified"]).count()
    won_leads = Lead.objects.filter(status="won").count()
    new_leads_today = Lead.objects.filter(created_at__gte=today_start).count()

    pending_bookings = ConsultationBooking.objects.filter(status="pending").count()
    confirmed_bookings = ConsultationBooking.objects.filter(
        status="confirmed", scheduled_date__gte=now.date()
    ).count()

    open_tickets = SupportTicket.objects.exclude(status__in=["resolved", "closed"]).count()
    unresolved_tickets = SupportTicket.objects.filter(status__in=["open", "in_progress", "waiting_admin"]).count()

    # ── Content ───────────────────────────────────────────────────────
    published_services = Service.objects.filter(status="published").count()
    published_blog_posts = BlogPost.objects.filter(status="published").count()
    draft_content = BlogPost.objects.filter(status="draft").count() + Service.objects.filter(status="draft").count()
    in_review_content = (
        BlogPost.objects.filter(status="in_review").count()
        + Service.objects.filter(status="in_review").count()
    )

    # ── AI Assistant ──────────────────────────────────────────────────
    active_conversations = AIConversation.objects.filter(is_active=True).count()
    total_conversations = AIConversation.objects.count()
    conversations_today = AIConversation.objects.filter(started_at__gte=today_start).count()

    # ── Notifications ─────────────────────────────────────────────────
    notifications_today = Notification.objects.filter(
        created_at__gte=today_start
    ).count()
    failed_notifications = Notification.objects.filter(status="failed").count()

    # ── Environment indicator ─────────────────────────────────────────
    from django.conf import settings
    debug = getattr(settings, "DEBUG", False)
    env_label = "DEVELOPMENT" if debug else "PRODUCTION"

    # ── Role breakdown (for a doughnut chart) ─────────────────────────
    role_breakdown = list(
        users_qs.values("role").annotate(count=Count("id")).order_by("role")
    )
    role_labels = [str(User.Role(row["role"]).label) for row in role_breakdown]
    role_data = [row["count"] for row in role_breakdown]

    # ── Signups over the last 14 days (for a line chart) ──────────────
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

    # ── Tenant tier breakdown table ───────────────────────────────────
    tenant_tiers = list(
        Tenant.objects.values("subscription_tier")
        .annotate(count=Count("id"))
        .order_by("subscription_tier")
    )

    # ── Leads by status (bar chart) ───────────────────────────────────
    leads_by_status = list(
        Lead.objects.values("status").annotate(count=Count("id")).order_by("status")
    )
    lead_status_labels = [
        str(dict(Lead.Status.choices).get(row["status"], row["status"]))
        for row in leads_by_status
    ]
    lead_status_data = [row["count"] for row in leads_by_status]

    # ── Leads by source channel (doughnut chart) ──────────────────────
    leads_by_channel = list(
        Lead.objects.exclude(source_channel="")
        .values("source_channel")
        .annotate(count=Count("id"))
        .order_by("source_channel")
    )
    channel_labels = [
        str(dict(Lead.SourceChannel.choices).get(row["source_channel"], row["source_channel"]))
        for row in leads_by_channel
    ]
    channel_data = [row["count"] for row in leads_by_channel]

    context.update(
        {
            "env_label": env_label,
            "env_css_class": f"env-badge--{env_label.lower()}",
            "kpi_cards": [
                {
                    "title": "Total Users",
                    "metric": total_users,
                    "footer": f"{active_users} active · {new_users_this_week} new this week",
                    "css_class": "",
                },
                {
                    "title": "Verified Emails",
                    "metric": verified_users,
                    "footer": f"{unverified_users} pending verification",
                    "css_class": "" if unverified_users == 0 else ("kpi-warning" if unverified_users < 10 else "kpi-danger"),
                },
                {
                    "title": "Total Leads",
                    "metric": total_leads,
                    "footer": f"{open_leads} open · {won_leads} won · {new_leads_today} today",
                    "css_class": "",
                },
                {
                    "title": "Open Leads",
                    "metric": open_leads,
                    "footer": f"{won_leads} won · {new_leads_today} new today",
                    "css_class": "",
                },
                {
                    "title": "Pending Bookings",
                    "metric": pending_bookings,
                    "footer": f"{confirmed_bookings} upcoming" if pending_bookings else "All clear",
                    "css_class": "" if pending_bookings == 0 else ("kpi-warning" if pending_bookings < 5 else "kpi-danger"),
                },
                {
                    "title": "Open Support Tickets",
                    "metric": unresolved_tickets,
                    "footer": f"{open_tickets} total · needs attention",
                    "css_class": "" if unresolved_tickets == 0 else ("kpi-warning" if unresolved_tickets < 3 else "kpi-danger"),
                },
                {
                    "title": "Live Services",
                    "metric": published_services,
                    "footer": f"{draft_content} drafts · {in_review_content} in review",
                    "css_class": "",
                },
                {
                    "title": "Published Articles",
                    "metric": published_blog_posts,
                    "footer": "live blog posts on site",
                    "css_class": "",
                },
                {
                    "title": "AI Conversations",
                    "metric": active_conversations,
                    "footer": f"{conversations_today} today · {total_conversations} total",
                    "css_class": "",
                },
                {
                    "title": "Notifications",
                    "metric": notifications_today,
                    "footer": f"last 24h · {failed_notifications} failed",
                    "css_class": "kpi-danger" if failed_notifications > 0 else "",
                },
                {
                    "title": "Locked Accounts",
                    "metric": locked_users,
                    "footer": "Security alert — investigate now" if locked_users else "No locked accounts",
                    "css_class": "" if locked_users == 0 else "kpi-danger",
                },
                {
                    "title": "Active Sessions",
                    "metric": active_sessions,
                    "footer": "live refresh tokens active",
                    "css_class": "",
                },
                {
                    "title": "Tenants",
                    "metric": total_tenants,
                    "footer": f"{active_tenants} active · {enterprise_tenants} enterprise",
                    "css_class": "",
                },
            ],
            "signup_chart_labels": json.dumps(signup_labels),
            "signup_chart_data": json.dumps(signup_data),
            "role_chart_labels": json.dumps(role_labels),
            "role_chart_data": json.dumps(role_data),
            "lead_status_labels": json.dumps(lead_status_labels),
            "lead_status_data": json.dumps(lead_status_data),
            "channel_labels": json.dumps(channel_labels),
            "channel_data": json.dumps(channel_data),
            "tenant_tiers": tenant_tiers,
            # System Health section variables
            "locked_users": locked_users,
            "failed_notifications": failed_notifications,
            "unresolved_tickets": unresolved_tickets,
            "draft_content": draft_content,
        }
    )
    return context