"""
apps/crm/api/urls.py
─────────────────────────
Mounted at /api/v1/crm/ from config/urls.py.
"""
from __future__ import annotations

from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("leads/contact/", views.ContactLeadCreateView.as_view(), name="lead-contact"),
    path("leads/quote/", views.QuoteRequestCreateView.as_view(), name="lead-quote"),
    path("bookings/consultations/", views.ConsultationBookingCreateView.as_view(), name="consultation-create"),
    path("bookings/availability/", views.AvailableSlotsView.as_view(), name="availability"),
    path("newsletter/subscribe/", views.NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
]
