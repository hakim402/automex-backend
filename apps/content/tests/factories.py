"""
apps/content/tests/factories.py
──────────────────────────────────
Small, explicit factory helpers (matches the style of apps.accounts.tests.factories)
— no factory_boy dependency, just plain functions with sensible defaults.
"""
from __future__ import annotations

from django.utils import timezone

from apps.content.models import (
    AICapability,
    BlogCategory,
    BlogPost,
    BlogTag,
    CaseStudy,
    Certification,
    FAQ,
    Industry,
    Partner,
    PortfolioProject,
    ServiceCategory,
    Technology,
    Service,
    TechExpertiseArea,
    TeamMember,
    Testimonial,
)
from apps.core.models import PublishableModel


def create_service_category(**kwargs) -> ServiceCategory:
    defaults = dict(name="Custom Software Development", slug="custom-software-development")
    defaults.update(kwargs)
    return ServiceCategory.objects.create(**defaults)


def create_technology(**kwargs) -> Technology:
    defaults = dict(name="Django", slug="django", category=Technology.Category.BACKEND)
    defaults.update(kwargs)
    return Technology.objects.create(**defaults)


def create_industry(*, language_code: str = "en", name: str = "Healthcare", slug: str = "healthcare", **kwargs) -> Industry:
    industry = Industry.objects.create(**kwargs)
    industry.set_current_language(language_code)
    industry.name = name
    industry.slug = slug
    industry.description = f"{name} industry description."
    industry.save()
    return industry


def create_service(
    *,
    language_code: str = "en",
    name: str = "Custom Software Development",
    slug: str = "custom-software-development",
    status: str = PublishableModel.Status.PUBLISHED,
    published: bool = True,
    **kwargs,
) -> Service:
    fields = dict(status=status)
    if published and status == PublishableModel.Status.PUBLISHED:
        fields["published_at"] = timezone.now()
    fields.update(kwargs)

    service = Service.objects.create(**fields)
    service.set_current_language(language_code)
    service.name = name
    service.slug = slug
    service.short_description = f"{name} short description."
    service.overview = f"{name} overview."
    service.save()
    return service


def create_case_study(
    *,
    language_code: str = "en",
    title: str = "Acme Corp Platform Rebuild",
    slug: str = "acme-corp-platform-rebuild",
    status: str = PublishableModel.Status.PUBLISHED,
    published: bool = True,
    **kwargs,
) -> CaseStudy:
    fields = dict(status=status)
    if published and status == PublishableModel.Status.PUBLISHED:
        fields["published_at"] = timezone.now()
    fields.update(kwargs)

    case_study = CaseStudy.objects.create(**fields)
    case_study.set_current_language(language_code)
    case_study.title = title
    case_study.slug = slug
    case_study.overview = f"{title} overview."
    case_study.save()
    return case_study


def create_blog_category(**kwargs) -> BlogCategory:
    defaults = dict(name="Engineering", slug="engineering")
    defaults.update(kwargs)
    return BlogCategory.objects.create(**defaults)


def create_blog_tag(**kwargs) -> BlogTag:
    defaults = dict(name="Django", slug="django")
    defaults.update(kwargs)
    return BlogTag.objects.create(**defaults)


def create_blog_post(
    *,
    language_code: str = "en",
    title: str = "How We Scaled Our Platform",
    slug: str = "how-we-scaled-our-platform",
    status: str = PublishableModel.Status.PUBLISHED,
    published: bool = True,
    **kwargs,
) -> BlogPost:
    fields = dict(status=status)
    if published and status == PublishableModel.Status.PUBLISHED:
        fields["published_at"] = timezone.now()
    fields.update(kwargs)

    post = BlogPost.objects.create(**fields)
    post.set_current_language(language_code)
    post.title = title
    post.slug = slug
    post.excerpt = f"{title} excerpt."
    post.content = f"{title} full content."
    post.save()
    return post


def create_faq(*, service=None, language_code: str = "en", question="What is your pricing?", **kwargs) -> FAQ:
    faq = FAQ.objects.create(service=service, **kwargs)
    faq.set_current_language(language_code)
    faq.question = question
    faq.answer = "It depends on project scope."
    faq.save()
    return faq


def create_team_member(**kwargs) -> TeamMember:
    defaults = dict(full_name="Jane Doe", slug="jane-doe", role_title="Lead Engineer")
    defaults.update(kwargs)
    return TeamMember.objects.create(**defaults)


def create_testimonial(**kwargs) -> Testimonial:
    defaults = dict(client_name="John Smith", client_company="Acme Corp", quote="Great team to work with.")
    defaults.update(kwargs)
    return Testimonial.objects.create(**defaults)


def create_partner(**kwargs) -> Partner:
    defaults = dict(
        name="AWS", slug="aws", partner_type=Partner.PartnerType.CLOUD,
        tier=Partner.Tier.PLATINUM, description="Cloud infrastructure partner.", is_active=True,
    )
    defaults.update(kwargs)
    return Partner.objects.create(**defaults)


def create_certification(**kwargs) -> Certification:
    defaults = dict(name="ISO 27001", issuer="BSI Group", is_active=True)
    defaults.update(kwargs)
    return Certification.objects.create(**defaults)


def create_ai_capability(**kwargs) -> AICapability:
    defaults = dict(
        name="Natural Language Processing", slug="nlp",
        description="Advanced NLP capabilities.",
        category=AICapability.Category.NLP,
        maturity_level=AICapability.MaturityLevel.PRODUCTION,
        is_active=True,
    )
    defaults.update(kwargs)
    return AICapability.objects.create(**defaults)


def create_tech_expertise(**kwargs) -> TechExpertiseArea:
    defaults = dict(
        name="Cloud Architecture", slug="cloud-architecture",
        description="Expert cloud architecture services.",
        category=TechExpertiseArea.Category.CLOUD,
        is_active=True,
    )
    defaults.update(kwargs)
    return TechExpertiseArea.objects.create(**defaults)


def create_portfolio_project(**kwargs) -> PortfolioProject:
    defaults = dict(
        title="E-Commerce Platform", slug="e-commerce-platform",
        short_description="Full-featured e-commerce platform.",
        completion_year=2024, is_published=True,
    )
    defaults.update(kwargs)
    return PortfolioProject.objects.create(**defaults)
