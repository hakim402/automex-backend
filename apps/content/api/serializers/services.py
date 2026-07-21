"""
apps/content/api/serializers/services.py
────────────────────────────────────────────
List serializer stays light (for grid/card rendering); detail serializer
carries the full landing-page payload including nested taxonomy, SEO,
all enterprise sub-models (hero images, process steps, deliverables,
add-ons, comparison rows, client logos, testimonials, documents, SLAs),
pricing information, key metrics, and related services.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.content.models import FAQ, Service

from .common import MediaAssetSerializer, SEOSerializerMixin
from .taxonomy import FAQSerializer, IndustrySerializer, ProcessStepSerializer, ServiceCategorySerializer, TechnologySerializer


# ──────────────────────────────────────────────────────────────────────────────
# List serializer — lightweight card/grid rendering
# ──────────────────────────────────────────────────────────────────────────────

class ServiceListSerializer(serializers.ModelSerializer):
    category   = ServiceCategorySerializer(read_only=True)
    hero_image = MediaAssetSerializer(read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "slug", "name", "short_description", "icon",
            "hero_image", "category", "is_featured", "order",
        ]


# ──────────────────────────────────────────────────────────────────────────────
# Enterprise sub-model inline serializers
# ──────────────────────────────────────────────────────────────────────────────

class ServiceHeroImageSerializer(serializers.Serializer):
    id       = serializers.UUIDField()
    image    = MediaAssetSerializer(allow_null=True)
    caption  = serializers.CharField()
    is_cover = serializers.BooleanField()
    order    = serializers.IntegerField()


class ServiceProcessStepItemSerializer(serializers.Serializer):
    id               = serializers.UUIDField()
    process_step     = ProcessStepSerializer()
    custom_title     = serializers.CharField(allow_blank=True)
    custom_description = serializers.CharField(allow_blank=True)
    order            = serializers.IntegerField()

    def to_representation(self, instance):
        title = instance.custom_title or (
            instance.process_step.safe_translation_getter("title", any_language=True) or ""
        )
        description = instance.custom_description or (
            instance.process_step.safe_translation_getter("description", any_language=True) or ""
        )
        return {
            "id": str(instance.id),
            "title": title,
            "description": description,
            "icon": instance.process_step.icon,
            "order": instance.order,
        }


class ServiceDeliverableSerializer(serializers.Serializer):
    id          = serializers.UUIDField()
    title       = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    icon        = serializers.CharField(allow_blank=True)
    order       = serializers.IntegerField()


class ServiceAddOnSerializer(serializers.Serializer):
    id                        = serializers.UUIDField()
    name                      = serializers.CharField()
    description               = serializers.CharField(allow_blank=True)
    price                     = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    is_included_in_enterprise = serializers.BooleanField()
    order                     = serializers.IntegerField()


class ServiceComparisonRowSerializer(serializers.Serializer):
    id               = serializers.UUIDField()
    feature_name     = serializers.CharField()
    standard_value   = serializers.CharField(allow_blank=True)
    premium_value    = serializers.CharField(allow_blank=True)
    enterprise_value = serializers.CharField(allow_blank=True)
    is_highlighted   = serializers.BooleanField()
    order            = serializers.IntegerField()


class ServiceClientLogoSerializer(serializers.Serializer):
    id          = serializers.UUIDField()
    logo        = MediaAssetSerializer(allow_null=True)
    client_name = serializers.CharField(allow_blank=True)
    client_url  = serializers.CharField(allow_blank=True)
    order       = serializers.IntegerField()


class ServiceTestimonialItemSerializer(serializers.Serializer):
    id          = serializers.UUIDField()
    testimonial_id = serializers.UUIDField()
    client_name = serializers.CharField()
    client_role = serializers.CharField(allow_blank=True)
    client_company = serializers.CharField(allow_blank=True)
    client_avatar = MediaAssetSerializer()
    quote       = serializers.CharField()
    rating      = serializers.IntegerField()
    is_featured = serializers.BooleanField()
    order       = serializers.IntegerField()

    def to_representation(self, instance):
        t = instance.testimonial
        return {
            "id": str(instance.id),
            "testimonial_id": str(t.id),
            "client_name": t.client_name,
            "client_role": t.client_role,
            "client_company": t.client_company,
            "client_avatar": MediaAssetSerializer(t.client_avatar).data if t.client_avatar else None,
            "quote": t.quote,
            "rating": t.rating,
            "is_featured": instance.is_featured,
            "order": instance.order,
        }


class ServiceDocumentSerializer(serializers.Serializer):
    id            = serializers.UUIDField()
    title         = serializers.CharField()
    description   = serializers.CharField(allow_blank=True)
    file          = MediaAssetSerializer(allow_null=True)
    document_type = serializers.CharField()
    document_type_display = serializers.SerializerMethodField()
    is_public     = serializers.BooleanField()
    order         = serializers.IntegerField()

    def get_document_type_display(self, obj):
        return obj.get_document_type_display()


class ServiceSLASerializer(serializers.Serializer):
    id             = serializers.UUIDField()
    guarantee_name = serializers.CharField()
    value          = serializers.CharField()
    description    = serializers.CharField(allow_blank=True)
    icon           = serializers.CharField(allow_blank=True)
    order          = serializers.IntegerField()


# ──────────────────────────────────────────────────────────────────────────────
# Detail serializer — full landing-page payload
# ──────────────────────────────────────────────────────────────────────────────

class ServiceDetailSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    category     = ServiceCategorySerializer(read_only=True)
    hero_image   = MediaAssetSerializer(read_only=True)
    thumbnail_image = MediaAssetSerializer(read_only=True)
    video_presentation = MediaAssetSerializer(read_only=True)
    brochure     = MediaAssetSerializer(read_only=True)
    technologies = TechnologySerializer(many=True, read_only=True)
    industries   = IndustrySerializer(many=True, read_only=True)
    faqs         = serializers.SerializerMethodField()

    # Pricing / delivery
    pricing_model_display = serializers.CharField(source="get_pricing_model_display", read_only=True)
    service_level_display = serializers.CharField(source="get_service_level_display", read_only=True)

    # Enterprise sub-models (all fetched via SerializerMethodField for prefetch efficiency)
    hero_images         = serializers.SerializerMethodField()
    process_steps       = serializers.SerializerMethodField()
    deliverables        = serializers.SerializerMethodField()
    add_ons             = serializers.SerializerMethodField()
    comparison_rows     = serializers.SerializerMethodField()
    client_logos        = serializers.SerializerMethodField()
    service_testimonials = serializers.SerializerMethodField()
    documents           = serializers.SerializerMethodField()
    slas                = serializers.SerializerMethodField()
    related_services    = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            # Identity
            "id", "slug", "name",
            # Content
            "short_description", "overview", "problems_we_solve",
            "features", "benefits", "icon",
            # Media
            "hero_image", "thumbnail_image", "video_presentation", "brochure",
            # Classification
            "category", "service_level", "service_level_display",
            "is_enterprise", "is_featured",
            # Taxonomy
            "technologies", "tech_stack_grouped", "industries",
            # Pricing & delivery
            "pricing_model", "pricing_model_display",
            "starting_price", "currency",
            "delivery_time_estimate", "team_size_range",
            # CTA
            "cta_text", "cta_url",
            # Metrics & enterprise features
            "key_metrics", "enterprise_features",
            # Enterprise sub-models
            "hero_images", "process_steps", "deliverables", "add_ons",
            "comparison_rows", "client_logos", "service_testimonials",
            "documents", "slas",
            # Relations
            "related_services", "faqs",
            # Meta
            "published_at", "seo",
        ]

    # ── FAQ (existing) ─────────────────────────────────────────────────────

    def get_faqs(self, obj: Service):
        language_code = self.context.get("language_code")
        qs = FAQ.objects.filter(service=obj, is_active=True)
        if language_code:
            qs = qs.language(language_code)
        return FAQSerializer(qs.order_by("order"), many=True, context=self.context).data

    # ── Enterprise sub-models ──────────────────────────────────────────────

    def _prefetched_or_query(self, obj, related_name, ordering):
        """Use prefetched data if available, otherwise query the DB."""
        if hasattr(obj, "_prefetched_objects_cache") and related_name in obj._prefetched_objects_cache:
            return obj._prefetched_objects_cache[related_name]
        return getattr(obj, related_name).order_by(*ordering)

    def get_hero_images(self, obj):
        items = self._prefetched_or_query(obj, "hero_images", ["order"])
        return ServiceHeroImageSerializer(items, many=True).data

    def get_process_steps(self, obj):
        items = self._prefetched_or_query(obj, "process_steps", ["order"])
        return ServiceProcessStepItemSerializer(items, many=True).data

    def get_deliverables(self, obj):
        items = self._prefetched_or_query(obj, "deliverables", ["order"])
        return ServiceDeliverableSerializer(items, many=True).data

    def get_add_ons(self, obj):
        items = self._prefetched_or_query(obj, "add_ons", ["order"])
        return ServiceAddOnSerializer(items, many=True).data

    def get_comparison_rows(self, obj):
        items = self._prefetched_or_query(obj, "comparison_rows", ["order"])
        return ServiceComparisonRowSerializer(items, many=True).data

    def get_client_logos(self, obj):
        items = self._prefetched_or_query(obj, "client_logos", ["order"])
        return ServiceClientLogoSerializer(items, many=True).data

    def get_service_testimonials(self, obj):
        items = self._prefetched_or_query(obj, "service_testimonials", ["-is_featured", "order"])
        return ServiceTestimonialItemSerializer(items, many=True).data

    def get_documents(self, obj):
        items = self._prefetched_or_query(obj, "documents", ["order"])
        return ServiceDocumentSerializer(items, many=True).data

    def get_slas(self, obj):
        items = self._prefetched_or_query(obj, "slas", ["order"])
        return ServiceSLASerializer(items, many=True).data

    def get_related_services(self, obj):
        language_code = self.context.get("language_code", "en")
        related = Service.objects.published().language(language_code).filter(
            pk__in=obj.related_services.values_list("pk", flat=True)
        )
        return ServiceListSerializer(related, many=True, context=self.context).data
