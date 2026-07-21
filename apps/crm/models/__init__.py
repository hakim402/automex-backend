"""
apps/crm/models/__init__.py
────────────────────────────────
Re-exports every CRM model:

    from apps.crm.models import Lead, ConsultationBooking, CostCalculatorRule
"""
from .leads import Lead, LeadActivity, NewsletterSubscriber, QuoteRequestDetail
from .booking import AvailabilitySlot, ConsultationBooking
from .calculator import CalculatorSubmission, ComplexityTier, CostCalculatorRule
from .tickets import SupportTicket, SupportTicketMessage

__all__ = [
    "Lead",
    "QuoteRequestDetail",
    "LeadActivity",
    "NewsletterSubscriber",
    "AvailabilitySlot",
    "ConsultationBooking",
    "ComplexityTier",
    "CostCalculatorRule",
    "CalculatorSubmission",
    "SupportTicket",
    "SupportTicketMessage",
]
