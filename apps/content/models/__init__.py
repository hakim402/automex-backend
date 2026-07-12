"""
apps/content/models/__init__.py
────────────────────────────────────
Re-exports every content model so Django's app registry sees them (models
split into submodules must still be importable from apps.content.models),
and so other apps/serializers can do:

    from apps.content.models import Service, CaseStudy, BlogPost
"""
from .taxonomy import FAQ, Industry, ProcessStep, ServiceCategory, Technology
from .services import Service
from .case_studies import CaseStudy, CaseStudyGalleryImage
from .blog import BlogCategory, BlogPost, BlogTag
from .team import TeamMember
from .testimonials import Testimonial

__all__ = [
    "ServiceCategory",
    "Technology",
    "Industry",
    "ProcessStep",
    "FAQ",
    "Service",
    "CaseStudy",
    "CaseStudyGalleryImage",
    "BlogCategory",
    "BlogTag",
    "BlogPost",
    "TeamMember",
    "Testimonial",
]
