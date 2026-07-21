"""
apps/content/api/views.py
──────────────────────────────
Read-only public content API. Every viewset:
  - is API-key gated (see mixins.PublicContentViewSetMixin), not JWT
  - resolves and activates the request language, chained via .language()
    so parler returns instances already bound to the right translation
  - exposes only published content (status=PUBLISHED, published_at<=now)
    for workflowed models; is_active=True for reference/lookup data
"""
from __future__ import annotations

from rest_framework import viewsets

from apps.content.models import (
    FAQ,
    AICapability,
    BlogCategory,
    BlogPost,
    BlogTag,
    CaseStudy,
    Certification,
    Industry,
    Partner,
    PortfolioProject,
    ProcessStep,
    Service,
    ServiceCategory,
    TeamMember,
    Technology,
    TechExpertiseArea,
    Testimonial,
)

from .filters import (
    AICapabilityFilter,
    BlogPostFilter,
    CaseStudyFilter,
    PartnerFilter,
    PortfolioProjectFilter,
    ServiceFilter,
    TechExpertiseAreaFilter,
)
from .mixins import PublicContentViewSetMixin, TranslatedSlugLookupMixin
from .serializers import (
    AICapabilitySerializer,
    BlogCategorySerializer,
    BlogPostDetailSerializer,
    BlogPostListSerializer,
    BlogTagSerializer,
    CaseStudyDetailSerializer,
    CaseStudyListSerializer,
    CertificationSerializer,
    FAQSerializer,
    IndustrySerializer,
    PartnerSerializer,
    PortfolioProjectDetailSerializer,
    PortfolioProjectListSerializer,
    ProcessStepSerializer,
    ServiceCategorySerializer,
    ServiceDetailSerializer,
    ServiceListSerializer,
    TeamMemberSerializer,
    TechnologySerializer,
    TechExpertiseAreaSerializer,
    TestimonialSerializer,
)

# Added import for drf-spectacular
from drf_spectacular.utils import extend_schema_view, extend_schema


# ──────────────────────────────────────────────────────────────────────────────
# TAXONOMY (reference/lookup data)
# ──────────────────────────────────────────────────────────────────────────────

class ServiceCategoryViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceCategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return ServiceCategory.objects.filter(is_active=True).order_by("order")


class TechnologyViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TechnologySerializer
    lookup_field = "slug"
    filterset_fields = ["category"]

    def get_queryset(self):
        return Technology.objects.filter(is_active=True).order_by("category", "order")


class IndustryViewSet(TranslatedSlugLookupMixin, PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = IndustrySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Industry.objects.filter(is_active=True).language(self.language_code).order_by("order")


class ProcessStepViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ProcessStepSerializer

    def get_queryset(self):
        return ProcessStep.objects.filter(is_active=True).language(self.language_code).order_by("order")


class FAQViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = FAQSerializer
    filterset_fields = ["category", "service"]

    def get_queryset(self):
        return FAQ.objects.filter(is_active=True).language(self.language_code).order_by("order")


# ──────────────────────────────────────────────────────────────────────────────
# SERVICES
# ──────────────────────────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(responses=ServiceListSerializer(many=True)),
    retrieve=extend_schema(responses=ServiceDetailSerializer),
)
class ServiceViewSet(TranslatedSlugLookupMixin, PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    filterset_class = ServiceFilter
    search_fields = ["translations__name", "translations__short_description"]
    ordering_fields = ["order", "published_at"]

    def get_queryset(self):
        qs = Service.objects.published().language(self.language_code)
        return qs.select_related(
            "category", "hero_image", "thumbnail_image",
            "video_presentation", "brochure",
        ).prefetch_related(
            "technologies", "industries",
            "hero_images__image",
            "process_steps__process_step",
            "deliverables",
            "add_ons",
            "comparison_rows",
            "client_logos__logo",
            "service_testimonials__testimonial__client_avatar",
            "documents__file",
            "slas",
            "related_services",
        )

    def get_serializer_class(self):
        return ServiceDetailSerializer if self.action == "retrieve" else ServiceListSerializer


# ──────────────────────────────────────────────────────────────────────────────
# CASE STUDIES
# ──────────────────────────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(responses=CaseStudyListSerializer(many=True)),
    retrieve=extend_schema(responses=CaseStudyDetailSerializer),
)
class CaseStudyViewSet(TranslatedSlugLookupMixin, PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    filterset_class = CaseStudyFilter
    search_fields = ["translations__title", "translations__overview"]
    ordering_fields = ["order", "published_at"]

    def get_queryset(self):
        qs = CaseStudy.objects.published().language(self.language_code)
        return qs.select_related("client_industry", "client_logo", "thumbnail").prefetch_related(
            "technologies", "gallery__media",
        )

    def get_serializer_class(self):
        return CaseStudyDetailSerializer if self.action == "retrieve" else CaseStudyListSerializer


# ──────────────────────────────────────────────────────────────────────────────
# BLOG
# ──────────────────────────────────────────────────────────────────────────────

class BlogCategoryViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogCategorySerializer
    lookup_field = "slug"
    queryset = BlogCategory.objects.all().order_by("order")


class BlogTagViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogTagSerializer
    lookup_field = "slug"
    queryset = BlogTag.objects.all().order_by("name")


@extend_schema_view(
    list=extend_schema(responses=BlogPostListSerializer(many=True)),
    retrieve=extend_schema(responses=BlogPostDetailSerializer),
)
class BlogPostViewSet(TranslatedSlugLookupMixin, PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    filterset_class = BlogPostFilter
    search_fields = ["translations__title", "translations__excerpt", "translations__content"]
    ordering_fields = ["published_at", "views_count"]

    def get_queryset(self):
        qs = BlogPost.objects.published().language(self.language_code)
        return qs.select_related("author", "category", "cover_image").prefetch_related("tags")

    def get_serializer_class(self):
        return BlogPostDetailSerializer if self.action == "retrieve" else BlogPostListSerializer


# ──────────────────────────────────────────────────────────────────────────────
# TEAM & TESTIMONIALS
# ──────────────────────────────────────────────────────────────────────────────

class TeamMemberViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        return TeamMember.objects.filter(is_active=True).select_related("photo").order_by("order")


class TestimonialViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TestimonialSerializer
    filterset_fields = ["related_service", "related_case_study", "is_featured"]

    def get_queryset(self):
        return Testimonial.objects.filter(is_published=True).select_related(
            "client_avatar", "related_case_study", "related_service",
        ).order_by("order")


# ──────────────────────────────────────────────────────────────────────────────
# PARTNERS & CERTIFICATIONS
# ──────────────────────────────────────────────────────────────────────────────

class PartnerViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PartnerSerializer
    filterset_class = PartnerFilter
    lookup_field = "slug"

    def get_queryset(self):
        return Partner.objects.filter(is_active=True).select_related("logo").order_by("order", "name")


class CertificationViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificationSerializer
    filterset_fields = ["related_services"]

    def get_queryset(self):
        return Certification.objects.filter(is_active=True).select_related("badge_image").order_by("order", "name")


# ──────────────────────────────────────────────────────────────────────────────
# AI CAPABILITIES & TECH EXPERTISE
# ──────────────────────────────────────────────────────────────────────────────

class AICapabilityViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AICapabilitySerializer
    filterset_class = AICapabilityFilter
    lookup_field = "slug"

    def get_queryset(self):
        return AICapability.objects.filter(is_active=True)\
            .select_related("cover_image")\
            .prefetch_related("technologies")\
            .order_by("order", "name")


class TechExpertiseAreaViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TechExpertiseAreaSerializer
    filterset_class = TechExpertiseAreaFilter
    lookup_field = "slug"

    def get_queryset(self):
        return TechExpertiseArea.objects.filter(is_active=True)\
            .prefetch_related("technologies", "case_studies")\
            .order_by("order", "name")


# ──────────────────────────────────────────────────────────────────────────────
# PORTFOLIO
# ──────────────────────────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(responses=PortfolioProjectListSerializer(many=True)),
    retrieve=extend_schema(responses=PortfolioProjectDetailSerializer),
)
class PortfolioProjectViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    filterset_class = PortfolioProjectFilter
    search_fields = ["title", "short_description", "client_name"]
    ordering_fields = ["order", "completion_year", "created_at"]

    def get_queryset(self):
        qs = PortfolioProject.objects.filter(is_published=True)
        return qs.select_related("cover_image", "industry")\
            .prefetch_related("technologies", "services", "gallery_images__image")

    def get_serializer_class(self):
        return PortfolioProjectDetailSerializer if self.action == "retrieve" else PortfolioProjectListSerializer