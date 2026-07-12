"""
apps/content/api/filters.py
────────────────────────────────
django-filter FilterSets for the public content API's list endpoints.
"""
from __future__ import annotations

import django_filters as filters

from apps.content.models import BlogPost, CaseStudy, Service


class ServiceFilter(filters.FilterSet):
    category    = filters.CharFilter(field_name="category__slug")
    technology  = filters.CharFilter(field_name="technologies__slug")
    industry    = filters.CharFilter(field_name="industries__translations__slug")
    is_featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Service
        fields = ["category", "technology", "industry", "is_featured"]


class CaseStudyFilter(filters.FilterSet):
    industry    = filters.CharFilter(field_name="client_industry__translations__slug")
    technology  = filters.CharFilter(field_name="technologies__slug")
    service     = filters.CharFilter(field_name="related_services__translations__slug")
    is_featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = CaseStudy
        fields = ["industry", "technology", "service", "is_featured"]


class BlogPostFilter(filters.FilterSet):
    category    = filters.CharFilter(field_name="category__slug")
    tag         = filters.CharFilter(field_name="tags__slug")
    is_featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = BlogPost
        fields = ["category", "tag", "is_featured"]
