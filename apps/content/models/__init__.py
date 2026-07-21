"""
apps/content/models/__init__.py
────────────────────────────────────
Re-exports every content model so Django's app registry sees them (models
split into submodules must still be importable from apps.content.models),
and so other apps/serializers can do:

    from apps.content.models import Service, CaseStudy, BlogPost
"""
from .taxonomy import FAQ, Industry, ProcessStep, ServiceCategory, Technology
from .services import (
    Service,
    ServiceHeroImage,
    ServiceProcessStep,
    ServiceDeliverable,
    ServiceAddOn,
    ServiceComparisonRow,
    ServiceClientLogo,
    ServiceTestimonial,
    ServiceDocument,
    ServiceSLA,
)
from .case_studies import CaseStudy, CaseStudyGalleryImage
from .blog import BlogAuthor, BlogCategory, BlogHeroImage, BlogPost, BlogTag
from .team import TeamMember
from .testimonials import Testimonial
from .portfolio import PortfolioGalleryImage, PortfolioProject
from .expertise import AICapability, TechExpertiseArea
from .partners import Certification, Partner

__all__ = [
    "ServiceCategory",
    "Technology",
    "Industry",
    "ProcessStep",
    "FAQ",
    "Service",
    "ServiceHeroImage",
    "ServiceProcessStep",
    "ServiceDeliverable",
    "ServiceAddOn",
    "ServiceComparisonRow",
    "ServiceClientLogo",
    "ServiceTestimonial",
    "ServiceDocument",
    "ServiceSLA",
    "CaseStudy",
    "CaseStudyGalleryImage",
    "BlogCategory",
    "BlogTag",
    "BlogAuthor",
    "BlogHeroImage",
    "BlogPost",
    "TeamMember",
    "Testimonial",
    "PortfolioProject",
    "PortfolioGalleryImage",
    "AICapability",
    "TechExpertiseArea",
    "Partner",
    "Certification",
]
