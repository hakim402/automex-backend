"""
apps/content/api/filters.py
────────────────────────────────
django-filter FilterSets for the public content API's list endpoints.
"""
from __future__ import annotations

import django_filters as filters

from apps.content.models import AICapability, BlogPost, CaseStudy, Partner, PortfolioProject, Service, TechExpertiseArea


class ServiceFilter(filters.FilterSet):
    category       = filters.CharFilter(field_name="category__slug")
    technology     = filters.CharFilter(field_name="technologies__slug")
    industry       = filters.CharFilter(field_name="industries__translations__slug")
    is_featured    = filters.BooleanFilter(field_name="is_featured")
    service_level  = filters.CharFilter(field_name="service_level")
    is_enterprise  = filters.BooleanFilter(field_name="is_enterprise")
    pricing_model  = filters.CharFilter(field_name="pricing_model")

    class Meta:
        model = Service
        fields = ["category", "technology", "industry", "is_featured", "service_level", "is_enterprise", "pricing_model"]


class CaseStudyFilter(filters.FilterSet):
    industry      = filters.CharFilter(field_name="client_industry__translations__slug")
    technology    = filters.CharFilter(field_name="technologies__slug")
    service       = filters.CharFilter(field_name="related_services__translations__slug")
    is_featured   = filters.BooleanFilter(field_name="is_featured")
    project_type  = filters.CharFilter(field_name="project_type")
    is_ai_project = filters.BooleanFilter(field_name="is_ai_project")

    class Meta:
        model = CaseStudy
        fields = ["industry", "technology", "service", "is_featured", "project_type", "is_ai_project"]


class BlogPostFilter(filters.FilterSet):
    category     = filters.CharFilter(field_name="category__slug")
    tag          = filters.CharFilter(field_name="tags__slug")
    is_featured  = filters.BooleanFilter(field_name="is_featured")
    content_type = filters.CharFilter(field_name="content_type")
    is_premium   = filters.BooleanFilter(field_name="is_premium")

    class Meta:
        model = BlogPost
        fields = ["category", "tag", "is_featured", "content_type", "is_premium"]


class PartnerFilter(filters.FilterSet):
    partner_type = filters.CharFilter(field_name="partner_type")
    tier         = filters.CharFilter(field_name="tier")
    is_active    = filters.BooleanFilter(field_name="is_active")

    class Meta:
        model = Partner
        fields = ["partner_type", "tier", "is_active"]


class AICapabilityFilter(filters.FilterSet):
    category       = filters.CharFilter(field_name="category")
    maturity_level = filters.CharFilter(field_name="maturity_level")

    class Meta:
        model = AICapability
        fields = ["category", "maturity_level"]


class TechExpertiseAreaFilter(filters.FilterSet):
    category = filters.CharFilter(field_name="category")

    class Meta:
        model = TechExpertiseArea
        fields = ["category"]


class PortfolioProjectFilter(filters.FilterSet):
    industry    = filters.CharFilter(field_name="industry__translations__slug")
    technology  = filters.CharFilter(field_name="technologies__slug")
    service     = filters.CharFilter(field_name="services__translations__slug")
    is_featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = PortfolioProject
        fields = ["industry", "technology", "service", "is_featured"]
