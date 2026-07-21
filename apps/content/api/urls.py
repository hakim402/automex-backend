"""
apps/content/api/urls.py
─────────────────────────────
Mounted at /api/v1/ from config/urls.py.
"""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from . import views

app_name = "content"

router = DefaultRouter(trailing_slash=True)
router.register("service-categories", views.ServiceCategoryViewSet, basename="service-category")
router.register("technologies", views.TechnologyViewSet, basename="technology")
router.register("industries", views.IndustryViewSet, basename="industry")
router.register("process-steps", views.ProcessStepViewSet, basename="process-step")
router.register("faqs", views.FAQViewSet, basename="faq")
router.register("services", views.ServiceViewSet, basename="service")
router.register("case-studies", views.CaseStudyViewSet, basename="case-study")
router.register("blog/categories", views.BlogCategoryViewSet, basename="blog-category")
router.register("blog/tags", views.BlogTagViewSet, basename="blog-tag")
router.register("blog/posts", views.BlogPostViewSet, basename="blog-post")
router.register("team", views.TeamMemberViewSet, basename="team-member")
router.register("testimonials", views.TestimonialViewSet, basename="testimonial")
router.register("partners", views.PartnerViewSet, basename="partner")
router.register("certifications", views.CertificationViewSet, basename="certification")
router.register("ai-capabilities", views.AICapabilityViewSet, basename="ai-capability")
router.register("tech-expertise", views.TechExpertiseAreaViewSet, basename="tech-expertise")
router.register("portfolio", views.PortfolioProjectViewSet, basename="portfolio")

urlpatterns = router.urls
