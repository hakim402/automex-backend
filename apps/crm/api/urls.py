"""
apps/crm/api/urls.py
─────────────────────────
Mounted at /api/v1/crm/ from config/urls.py.
Includes: public write endpoints, dashboard (JWT), guest (API-key).
"""
from __future__ import annotations

from django.urls import include, path

from . import views
from .dashboard_views import (
    DashboardBookingCancelView,
    DashboardBookingDetailView,
    DashboardBookingListView,
    DashboardBookingRescheduleView,
    DashboardCalculationConvertView,
    DashboardCalculationListView,
    DashboardRequestDetailView,
    DashboardRequestListView,
    DashboardRequestMessageView,
    DashboardSummaryView,
    DashboardTicketDetailView,
    DashboardTicketListView,
    DashboardTicketMessageView,
)
from .guest_views import (
    GuestRequestDetailView,
    GuestRequestListView,
    GuestTicketCreateView,
    GuestTicketDetailView,
    GuestTicketMessageView,
)

app_name = "crm"

# ── Public write endpoints (API-key gated) ────────────────────────────────
public_urlpatterns = [
    path("leads/contact/", views.ContactLeadCreateView.as_view(), name="lead-contact"),
    path("leads/quote/", views.QuoteRequestCreateView.as_view(), name="lead-quote"),
    path("bookings/consultations/", views.ConsultationBookingCreateView.as_view(), name="consultation-create"),
    path("bookings/availability/", views.AvailableSlotsView.as_view(), name="availability"),
    path("newsletter/subscribe/", views.NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
]

# ── Dashboard endpoints (JWT-authenticated) ────────────────────────────────
dashboard_urlpatterns = [
    path("dashboard/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/requests/", DashboardRequestListView.as_view(), name="dashboard-requests"),
    path("dashboard/requests/<uuid:pk>/", DashboardRequestDetailView.as_view(), name="dashboard-request-detail"),
    path("dashboard/requests/<uuid:pk>/message/", DashboardRequestMessageView.as_view(), name="dashboard-request-message"),
    path("dashboard/bookings/", DashboardBookingListView.as_view(), name="dashboard-bookings"),
    path("dashboard/bookings/<uuid:pk>/", DashboardBookingDetailView.as_view(), name="dashboard-booking-detail"),
    path("dashboard/bookings/<uuid:pk>/reschedule/", DashboardBookingRescheduleView.as_view(), name="dashboard-booking-reschedule"),
    path("dashboard/bookings/<uuid:pk>/cancel/", DashboardBookingCancelView.as_view(), name="dashboard-booking-cancel"),
    path("dashboard/tickets/", DashboardTicketListView.as_view(), name="dashboard-tickets"),
    path("dashboard/tickets/<uuid:pk>/", DashboardTicketDetailView.as_view(), name="dashboard-ticket-detail"),
    path("dashboard/tickets/<uuid:pk>/messages/", DashboardTicketMessageView.as_view(), name="dashboard-ticket-message"),
    path("dashboard/calculations/", DashboardCalculationListView.as_view(), name="dashboard-calculations"),
    path("dashboard/calculations/<uuid:pk>/convert/", DashboardCalculationConvertView.as_view(), name="dashboard-calculation-convert"),
]

# ── Guest endpoints (API-key gated, token-based tracking) ──────────────────
guest_urlpatterns = [
    path("guest/requests/", GuestRequestListView.as_view(), name="guest-requests"),
    path("guest/requests/<uuid:pk>/", GuestRequestDetailView.as_view(), name="guest-request-detail"),
    path("guest/tickets/", GuestTicketCreateView.as_view(), name="guest-tickets-create"),
    path("guest/tickets/<uuid:pk>/", GuestTicketDetailView.as_view(), name="guest-ticket-detail"),
    path("guest/tickets/<uuid:pk>/messages/", GuestTicketMessageView.as_view(), name="guest-ticket-message"),
]

urlpatterns = public_urlpatterns + dashboard_urlpatterns + guest_urlpatterns
