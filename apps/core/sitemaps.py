"""
apps/core/sitemaps.py
────────────────────────
django.contrib.sitemaps classes, served at /sitemap.xml (wired in
config/urls.py). Every URL points at settings.FRONTEND_BASE_URL's host —
the public Next.js site, not this API's own domain — since that's what
search engines actually need to crawl, achieved via get_domain()/protocol
overrides rather than django.contrib.sites (not installed here).

ASSUMPTION (documented, easy to change): URLs are flat, English-default,
no locale prefix — e.g. {FRONTEND_BASE_URL}/services/{slug}/. If your
Next.js routing uses locale-prefixed paths (e.g. /en/services/{slug}),
adjust the `location()` methods below accordingly. Full multi-language
sitemap entries (one per translation, with hreflang alternates) can be
added later via Sitemap.i18n/alternates once the frontend's URL scheme
for non-default languages is finalized — deliberately kept simple here
rather than guessing an unconfirmed routing structure.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap

from apps.content.models import BlogPost, CaseStudy, Service

_frontend = urlsplit(settings.FRONTEND_BASE_URL)


class _FrontendDomainSitemapMixin:
    """
    Django's Sitemap._urls() always builds
    f"{protocol}://{domain}{self._location(item)}" — location() must
    return a bare path, and the domain normally comes from
    django.contrib.sites (not installed here). Overriding get_domain()
    and `protocol` here points every URL at FRONTEND_BASE_URL's host
    regardless of what host Django itself is served under, without
    needing the sites framework at all.
    """

    protocol = _frontend.scheme or "https"

    def get_domain(self, site=None) -> str:
        return _frontend.netloc


class ServiceSitemap(_FrontendDomainSitemapMixin, Sitemap):
    def items(self):
        return Service.objects.published().language("en")

    def location(self, obj: Service) -> str:
        slug = obj.safe_translation_getter("slug", language_code="en", any_language=True)
        return f"/services/{slug}/"

    def lastmod(self, obj: Service):
        return obj.updated_at

    def priority(self, obj: Service) -> float:
        return float(obj.sitemap_priority)

    def changefreq(self, obj: Service) -> str:
        return obj.sitemap_changefreq


class CaseStudySitemap(_FrontendDomainSitemapMixin, Sitemap):
    def items(self):
        return CaseStudy.objects.published().language("en")

    def location(self, obj: CaseStudy) -> str:
        slug = obj.safe_translation_getter("slug", language_code="en", any_language=True)
        return f"/case-studies/{slug}/"

    def lastmod(self, obj: CaseStudy):
        return obj.updated_at

    def priority(self, obj: CaseStudy) -> float:
        return float(obj.sitemap_priority)

    def changefreq(self, obj: CaseStudy) -> str:
        return obj.sitemap_changefreq


class BlogPostSitemap(_FrontendDomainSitemapMixin, Sitemap):
    def items(self):
        return BlogPost.objects.published().language("en")

    def location(self, obj: BlogPost) -> str:
        slug = obj.safe_translation_getter("slug", language_code="en", any_language=True)
        return f"/blog/{slug}/"

    def lastmod(self, obj: BlogPost):
        return obj.updated_at

    def priority(self, obj: BlogPost) -> float:
        return float(obj.sitemap_priority)

    def changefreq(self, obj: BlogPost) -> str:
        return obj.sitemap_changefreq


class StaticViewSitemap(_FrontendDomainSitemapMixin, Sitemap):
    """
    Marketing pages with no backing model — adjust this list to match your
    actual Next.js routes.
    """

    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return ["", "services/", "case-studies/", "blog/", "about/", "contact/"]

    def location(self, item: str) -> str:
        return f"/{item}"
