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

from django.shortcuts import get_object_or_404
from django.utils import translation
from django.db.models import Prefetch
from rest_framework import viewsets
from rest_framework.throttling import ScopedRateThrottle

from apps.content.models import (
    FAQ,
    AICapability,
    BlogCategory,
    BlogHeroImage,
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
    ServiceDeliverable,
    ServiceAddOn,
    ServiceComparisonRow,
    ServiceClientLogo,
    ServiceDocument,
    ServiceHeroImage,
    ServiceSLA,
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
        return ServiceCategory.objects.filter(is_active=True).language(self.language_code).select_related("icon_image").order_by("order")


class TechnologyViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TechnologySerializer
    lookup_field = "slug"
    filterset_fields = ["category"]

    def get_queryset(self):
        return Technology.objects.filter(is_active=True).language(self.language_code).select_related("logo").order_by("category", "order")


class IndustryViewSet(TranslatedSlugLookupMixin, PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = IndustrySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Industry.objects.filter(is_active=True).language(self.language_code).select_related("icon_image").order_by("order")


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
        lang = self.language_code
        return qs.select_related(
            "category", "hero_image", "thumbnail_image",
            "video_presentation", "brochure",
        ).prefetch_related(
            "technologies", "industries",
            Prefetch("hero_images", queryset=ServiceHeroImage.objects.language(lang).select_related("image")),
            "process_steps__process_step",
            Prefetch("deliverables", queryset=ServiceDeliverable.objects.language(lang)),
            Prefetch("add_ons", queryset=ServiceAddOn.objects.language(lang)),
            Prefetch("comparison_rows", queryset=ServiceComparisonRow.objects.language(lang)),
            Prefetch("client_logos", queryset=ServiceClientLogo.objects.language(lang).select_related("logo")),
            "service_testimonials__testimonial__client_avatar",
            Prefetch("documents", queryset=ServiceDocument.objects.language(lang).select_related("file")),
            Prefetch("slas", queryset=ServiceSLA.objects.language(lang)),
            Prefetch("related_services", queryset=Service.objects.published().language(lang).select_related("category", "hero_image", "thumbnail_image")),
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
        return qs.select_related(
            "client_industry", "client_logo", "thumbnail", "testimonial",
        ).prefetch_related(
            "technologies", "gallery__media", "related_services",
        )

    def get_serializer_class(self):
        return CaseStudyDetailSerializer if self.action == "retrieve" else CaseStudyListSerializer


# ──────────────────────────────────────────────────────────────────────────────
# BLOG
# ──────────────────────────────────────────────────────────────────────────────

class BlogCategoryViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogCategorySerializer
    lookup_field = "slug"

    def get_queryset(self):
        return BlogCategory.objects.all().language(self.language_code).order_by("order")


class BlogTagViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = BlogTagSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return BlogTag.objects.all().language(self.language_code).order_by("slug")


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
        lang = self.language_code
        return qs.select_related(
            "author", "category", "cover_image", "thumbnail_image",
        ).prefetch_related(
            "tags",
            Prefetch("hero_images", queryset=BlogHeroImage.objects.language(lang).select_related("image")),
            "related_services",
            "related_case_studies",
        )

    def get_serializer_class(self):
        return BlogPostDetailSerializer if self.action == "retrieve" else BlogPostListSerializer


# ──────────────────────────────────────────────────────────────────────────────
# TEAM & TESTIMONIALS
# ──────────────────────────────────────────────────────────────────────────────

class TeamMemberViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TeamMemberSerializer

    def get_queryset(self):
        return TeamMember.objects.filter(is_active=True).language(self.language_code)\
            .select_related("photo")\
            .prefetch_related("projects_showcase")\
            .order_by("order")


class TestimonialViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TestimonialSerializer
    filterset_fields = ["related_service", "related_case_study", "is_featured"]

    def get_queryset(self):
        return Testimonial.objects.filter(is_published=True).language(self.language_code).select_related(
            "client_avatar", "related_case_study", "related_service",
            "client_industry", "video_thumbnail",
        ).order_by("order")


# ──────────────────────────────────────────────────────────────────────────────
# PARTNERS & CERTIFICATIONS
# ──────────────────────────────────────────────────────────────────────────────

class PartnerViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = PartnerSerializer
    filterset_class = PartnerFilter
    lookup_field = "slug"

    def get_queryset(self):
        return Partner.objects.filter(is_active=True).language(self.language_code).select_related("logo").order_by("order")


class CertificationViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificationSerializer
    filterset_fields = ["related_services"]

    def get_queryset(self):
        return Certification.objects.filter(is_active=True).language(self.language_code)\
            .select_related("badge_image")\
            .prefetch_related("related_services")\
            .order_by("order")


# ──────────────────────────────────────────────────────────────────────────────
# AI CAPABILITIES & TECH EXPERTISE
# ──────────────────────────────────────────────────────────────────────────────

class AICapabilityViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = AICapabilitySerializer
    filterset_class = AICapabilityFilter
    lookup_field = "slug"

    def get_queryset(self):
        return AICapability.objects.filter(is_active=True).language(self.language_code)\
            .select_related("cover_image")\
            .prefetch_related("technologies", "related_services")\
            .order_by("order")


class TechExpertiseAreaViewSet(PublicContentViewSetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TechExpertiseAreaSerializer
    filterset_class = TechExpertiseAreaFilter
    lookup_field = "slug"

    def get_queryset(self):
        return TechExpertiseArea.objects.filter(is_active=True).language(self.language_code)\
            .prefetch_related(
                "technologies",
                Prefetch("case_studies", queryset=CaseStudy.objects.select_related("thumbnail", "client_industry", "client_logo")),
            )\
            .order_by("order")


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
    search_fields = ["translations__title", "translations__short_description", "translations__client_name"]
    ordering_fields = ["order", "completion_year", "created_at"]

    def get_queryset(self):
        qs = PortfolioProject.objects.filter(is_published=True).language(self.language_code)
        return qs.select_related("cover_image", "industry")\
            .prefetch_related("technologies", "services", "gallery_images__image")

    def get_serializer_class(self):
        return PortfolioProjectDetailSerializer if self.action == "retrieve" else PortfolioProjectListSerializer