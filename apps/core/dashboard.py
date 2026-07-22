"""
apps/core/dashboard.py
───────────────────────────
Feeds the custom Unfold admin homepage (templates/admin/index.html)
with 6 essential KPI cards + chart data formatted for Unfold's native
chart components (bar, line).

Wire it up in settings_unfold_additions.py:

    UNFOLD_ADDITIONS = {
        ...
        "DASHBOARD_CALLBACK": "apps.core.dashboard.dashboard_callback",
    }
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpRequest
from django.utils import timezone


def get_site_symbol(request):
    """Returns a monogram/symbol for the Unfold sidebar header."""
    return "◈"  # Geometric diamond


def dashboard_callback(request: HttpRequest, context: dict) -> dict:
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # ── Accounts ──────────────────────────────────────────────────────
    from apps.accounts.models import Tenant, User, UserRefreshToken

    users_qs = User.objects.filter(deleted_at__isnull=True)
    total_users = users_qs.count()
    active_users = users_qs.filter(is_active=True).count()
    verified_users = users_qs.filter(is_email_verified=True).count()
    locked_users = users_qs.filter(locked_until__gt=now).count()
    new_users_this_week = users_qs.filter(created_at__gte=week_ago).count()
    new_users_this_month = users_qs.filter(created_at__gte=month_ago).count()
    unverified_users = total_users - verified_users

    total_tenants = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(is_active=True).count()
    enterprise_tenants = Tenant.objects.filter(subscription_tier=Tenant.SubscriptionTier.ENTERPRISE).count()

    active_sessions = UserRefreshToken.objects.filter(
        revoked=False, expires_at__gt=now
    ).count()

    # ── CRM ───────────────────────────────────────────────────────────
    from apps.crm.models import ConsultationBooking, Lead, SupportTicket

    total_leads = Lead.objects.count()
    open_leads = Lead.objects.filter(status__in=["new", "contacted", "qualified"]).count()
    won_leads = Lead.objects.filter(status="won").count()
    new_leads_today = Lead.objects.filter(created_at__gte=today_start).count()
    new_leads_this_week = Lead.objects.filter(created_at__gte=week_ago).count()

    pending_bookings = ConsultationBooking.objects.filter(status="pending").count()
    confirmed_bookings = ConsultationBooking.objects.filter(
        status="confirmed", scheduled_date__gte=now.date()
    ).count()
    bookings_today = ConsultationBooking.objects.filter(scheduled_date=now.date()).count()

    open_tickets = SupportTicket.objects.exclude(status__in=["resolved", "closed"]).count()
    unresolved_tickets = SupportTicket.objects.filter(
        status__in=["open", "in_progress", "waiting_admin"]
    ).count()
    resolved_tickets = SupportTicket.objects.filter(status="resolved").count()

    # ── Content ───────────────────────────────────────────────────────
    from apps.content.models import (
        BlogPost, CaseStudy, Certification, FAQ, Partner,
        PortfolioProject, Service, TeamMember,
    )

    published_services = Service.objects.filter(status="published").count()
    draft_services = Service.objects.filter(status="draft").count()
    published_blog_posts = BlogPost.objects.filter(status="published").count()
    draft_blog = BlogPost.objects.filter(status="draft").count()
    published_case_studies = CaseStudy.objects.filter(status="published").count()
    published_portfolio = PortfolioProject.objects.filter(is_published=True).count()

    draft_content = (
        BlogPost.objects.filter(status="draft").count()
        + Service.objects.filter(status="draft").count()
        + CaseStudy.objects.filter(status="draft").count()
    )
    in_review_content = (
        BlogPost.objects.filter(status="in_review").count()
        + Service.objects.filter(status="in_review").count()
        + CaseStudy.objects.filter(status="in_review").count()
    )

    total_faqs = FAQ.objects.filter(is_active=True).count()
    total_team = TeamMember.objects.filter(is_active=True).count()
    total_partners = Partner.objects.filter(is_active=True).count()
    total_certifications = Certification.objects.filter(is_active=True).count()

    # ── AI Assistant ──────────────────────────────────────────────────
    from apps.assistant.models import AIConversation, AIKnowledgeEntry

    active_conversations = AIConversation.objects.filter(is_active=True).count()
    total_conversations = AIConversation.objects.count()
    conversations_today = AIConversation.objects.filter(started_at__gte=today_start).count()
    total_knowledge_entries = AIKnowledgeEntry.objects.filter(is_active=True).count()
    leads_captured = AIConversation.objects.filter(lead_captured=True).count()

    # ── Notifications ─────────────────────────────────────────────────
    from apps.notifications.models import Notification

    notifications_today = Notification.objects.filter(created_at__gte=today_start).count()
    failed_notifications = Notification.objects.filter(status="failed").count()
    pending_notifications = Notification.objects.filter(status="pending").count()

    # ── Environment indicator ─────────────────────────────────────────
    debug = getattr(settings, "DEBUG", False)
    env_label = "DEVELOPMENT" if debug else "PRODUCTION"
    env_css_class = f"env-badge--{env_label.lower()}"

    # ── Role breakdown (doughnut chart) ───────────────────────────────
    role_breakdown = list(
        users_qs.values("role").annotate(count=Count("id")).order_by("role")
    )
    role_labels = [str(User.Role(row["role"]).label) for row in role_breakdown]
    role_data = [row["count"] for row in role_breakdown]

    # ── Signups over last 14 days (line chart) ────────────────────────
    end_date = now.date()
    start_date = end_date - timedelta(days=13)
    daily_signups = (
        users_qs.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    signup_by_day = {row["day"]: row["count"] for row in daily_signups}
    signup_labels = []
    signup_data = []
    for i in range(14):
        day = start_date + timedelta(days=i)
        signup_labels.append(day.strftime("%b %d"))
        signup_data.append(signup_by_day.get(day, 0))

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

    # ── Content health breakdown ──────────────────────────────────────
    content_health_labels = ["Services", "Blog Posts", "Case Studies", "Portfolio"]
    content_health_data = [
        published_services,
        published_blog_posts,
        published_case_studies,
        published_portfolio,
    ]

    context.update(
        {
            "env_label": env_label,
            "env_css_class": env_css_class,
            # ── 6 Essential KPI Cards ─────────────────────────────────
            "kpi_cards": [
                {
                    "title": "Users",
                    "metric": total_users,
                    "icon": "person",
                    "footer": (
                        f"{active_users} active · {verified_users} verified · "
                        f"{new_users_this_week} new this week"
                        + (f" · {locked_users} locked" if locked_users else "")
                    ),
                },
                {
                    "title": "Leads",
                    "metric": total_leads,
                    "icon": "person_search",
                    "footer": (
                        f"{open_leads} open · {won_leads} won"
                        + (f" · +{new_leads_today} today" if new_leads_today else "")
                    ),
                },
                {
                    "title": "Bookings & Tickets",
                    "metric": f"{pending_bookings}/{unresolved_tickets}",
                    "icon": "calendar_month",
                    "footer": (
                        f"{pending_bookings} pending bookings"
                        + (f" · {bookings_today} today" if bookings_today else "")
                        + f"  |  {unresolved_tickets} open tickets"
                        + (f" · {resolved_tickets} resolved" if resolved_tickets else "")
                    ),
                },
                {
                    "title": "Content",
                    "metric": published_services + published_blog_posts + published_case_studies,
                    "icon": "article",
                    "footer": (
                        f"{published_services} services · {published_blog_posts} articles · "
                        f"{published_case_studies} case studies"
                        + (f" · {draft_content} drafts" if draft_content else "")
                    ),
                },
                {
                    "title": "AI Assistant",
                    "metric": active_conversations,
                    "icon": "psychology",
                    "footer": (
                        f"{conversations_today} conversations today · "
                        f"{leads_captured} leads captured · "
                        f"{total_knowledge_entries} knowledge entries"
                    ),
                },
                {
                    "title": "System Health",
                    "metric": (
                        "✓ All Clear"
                        if (locked_users + failed_notifications + unresolved_tickets == 0)
                        else f"{locked_users + failed_notifications + unresolved_tickets} issues"
                    ),
                    "icon": "monitoring",
                    "footer": (
                        (f"{locked_users} locked accounts" if locked_users else "No locked accounts")
                        + " · "
                        + (f"{failed_notifications} failed notifications" if failed_notifications else "No failed notifications")
                        + " · "
                        + (f"{unresolved_tickets} unresolved tickets" if unresolved_tickets else "No unresolved tickets")
                    ),
                },
            ],
            # ── Charts (formatted for Unfold native chart components) ─
            # Signups — line chart
            "signup_chart_data": json.dumps({
                "labels": signup_labels,
                "datasets": [{
                    "label": "Signups",
                    "data": signup_data,
                    "borderColor": "rgb(99, 102, 241)",
                    "backgroundColor": "rgba(99, 102, 241, 0.08)",
                    "tension": 0.35,
                    "fill": True,
                    "pointRadius": 3,
                    "pointHoverRadius": 6,
                }],
            }),
            # Roles — doughnut (raw Chart.js)
            "role_chart_labels": json.dumps(role_labels),
            "role_chart_data": json.dumps(role_data),
            # Lead status — bar chart
            "lead_status_chart_data": json.dumps({
                "labels": lead_status_labels,
                "datasets": [{
                    "label": "Leads",
                    "data": lead_status_data,
                    "backgroundColor": [
                        "rgb(99, 102, 241)", "rgb(234, 179, 8)", "rgb(34, 197, 94)",
                        "rgb(239, 68, 68)", "rgb(168, 85, 247)", "rgb(59, 130, 246)",
                        "rgb(251, 146, 60)", "rgb(156, 163, 175)",
                    ],
                    "borderRadius": 6,
                    "borderSkipped": False,
                }],
            }),
            # Source channel — doughnut (raw Chart.js)
            "channel_labels": json.dumps(channel_labels),
            "channel_data": json.dumps(channel_data),
            # Content health — bar chart
            "content_health_chart_data": json.dumps({
                "labels": content_health_labels,
                "datasets": [{
                    "label": "Published",
                    "data": content_health_data,
                    "backgroundColor": [
                        "rgb(99, 102, 241)", "rgb(234, 179, 8)",
                        "rgb(34, 197, 94)", "rgb(168, 85, 247)",
                    ],
                    "borderRadius": 6,
                    "borderSkipped": False,
                }],
            }),
            # ── Quick-action context ──────────────────────────────────
            "total_leads": total_leads,
            "total_users": total_users,
            "published_services": published_services,
            "total_conversations": total_conversations,
            "draft_content": draft_content,
        }
    )
    return context
