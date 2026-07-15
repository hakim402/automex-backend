"""
apps/core/middleware.py
────────────────────────────
RedirectMiddleware — serves 301/302 redirects from the Redirect model.

Deliberately implemented via process_response() gated on status_code==404,
not a pre-URL-resolution check on every request: the vast majority of
requests resolve successfully, and there's no reason to pay a lookup cost
on every single one just to handle the rare retired-URL case. Results are
cached briefly (Redis, via Django's cache framework) since a redirect
that gets hit at all tends to get hit repeatedly (old bookmark, external
backlink, etc.) in a short window.
"""
from __future__ import annotations

from django.core.cache import cache
from django.db.models import F
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect

from .models import Redirect

_CACHE_KEY_PREFIX = "redirect_lookup:"
_CACHE_TTL_SECONDS = 300
_MISS_SENTINEL = object()


class RedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if response.status_code != 404:
            return response

        redirect = self._lookup(request.path)
        if redirect is None:
            return response

        # Always increments against the live DB value via F() — the cached
        # lookup above is for the (rarely-changing) redirect target only,
        # never for hit_count, which must never be read from a stale cache.
        Redirect.objects.filter(pk=redirect["id"]).update(hit_count=F("hit_count") + 1)

        redirect_cls = HttpResponsePermanentRedirect if redirect["is_permanent"] else HttpResponseRedirect
        return redirect_cls(redirect["new_path"])

    @staticmethod
    def _lookup(path: str) -> dict | None:
        cache_key = f"{_CACHE_KEY_PREFIX}{path}"
        cached = cache.get(cache_key, _MISS_SENTINEL)
        if cached is not _MISS_SENTINEL:
            return cached

        row = (
            Redirect.objects.filter(old_path=path, is_active=True)
            .values("id", "new_path", "is_permanent")
            .first()
        )
        cache.set(cache_key, row, _CACHE_TTL_SECONDS)
        return row
