"""Web search through a fallback chain, plus the Google Fact Check Tools API.

The chain comes from `search.providers` in config.yaml, e.g. searxng → serper → selenium. SearXNG
and Selenium expand into one attempt per engine (searxng:google, searxng:duckduckgo, ...). The first
attempt that answers wins; empty results are a valid answer. An attempt that errors (blocked,
CAPTCHA, out of credits, down) is put on cooldown and the next one is tried. Failures and recoveries
are recorded in the business_critical table (see search_health.py).
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from functools import partial

import httpx

from app.clients import queue_redis
from app.config import Config, get_config
from app.log import log
from app.pipeline import browser_search
from app.pipeline.search_health import ALL_PROVIDERS, SearchHealth


@dataclass
class Hit:
    url: str
    title: str
    snippet: str
    served_by: str = ""
    published: str = ""


class SearchError(Exception):
    """No provider could answer."""


class EngineFailure(Exception):
    """One engine or provider failed for this query (blocked, CAPTCHA, HTTP error)."""


class ProviderDown(EngineFailure):
    """The whole provider is unreachable (e.g. the SearXNG container is down): skip all its engines."""


Runner = Callable[[str, "list[str] | None", Config], Awaitable[list[Hit]]]


@dataclass
class Attempt:
    name: str       # recorded in logs and business_critical, e.g. "searxng:google"
    provider: str   # e.g. "searxng"
    run: Runner


def _with_sites(query: str, domains: list[str] | None) -> str:
    if not domains:
        return query
    return f"{query} (" + " OR ".join(f"site:{d}" for d in domains) + ")"


async def _searxng(engine: str, query: str, domains: list[str] | None, config: Config) -> list[Hit]:
    settings = config.search.searxng
    params = {"q": _with_sites(query, domains), "format": "json", "engines": engine,
              "language": config.search.language, "safesearch": 0}
    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            response = await client.get(settings.url.rstrip("/") + "/search", params=params,
                                        headers={"X-Real-IP": "127.0.0.1"})
    except httpx.TransportError as exc:
        raise ProviderDown(f"SearXNG unreachable: {type(exc).__name__}: {exc}") from exc
    if response.status_code != 200:
        raise ProviderDown(f"SearXNG returned HTTP {response.status_code}")
    data = response.json()
    for name, reason in data.get("unresponsive_engines", []):
        if name == engine:
            raise EngineFailure(f"{engine}: {reason}")
    # SearXNG silently queries all engines when it doesn't know the name; keep only the asked-for engine.
    results = [r for r in data.get("results", []) if engine in (r.get("engines") or [r.get("engine")])]
    return [Hit(r.get("url", ""), r.get("title", ""), r.get("content", ""), published=_day(r.get("publishedDate")))
            for r in results][: config.search.results_per_query]


RELATIVE_DATE = re.compile(r"^(\d+|an?)\s+(minute|hour|day|week|month|year)s?\s+ago$", re.IGNORECASE)
UNIT_DAYS = {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}


def _day(value: object, today: date | None = None) -> str:
    """A publication date as YYYY-MM-DD where possible: ISO timestamps are trimmed, and relative ones
    like Serper's "3 days ago" become dates (approximate for months and years). Anything else as given."""
    text = str(value or "").strip()
    if len(text) >= 10 and text[4:5] == "-":
        return text[:10]
    match = RELATIVE_DATE.match(text)
    if match:
        amount = 1 if match.group(1).lower() in ("a", "an") else int(match.group(1))
        days = amount * UNIT_DAYS[match.group(2).lower()]
        return ((today or datetime.now(UTC).date()) - timedelta(days=days)).isoformat()
    return text


def _raise_for(provider: str, response: httpx.Response) -> None:
    if response.status_code >= 400:
        raise EngineFailure(f"{provider} returned HTTP {response.status_code}: {response.text[:200]}")


async def _serper(query: str, domains: list[str] | None, config: Config) -> list[Hit]:
    s = config.search
    async with httpx.AsyncClient(timeout=s.api_timeout_seconds) as client:
        r = await client.post("https://google.serper.dev/search", headers={"X-API-KEY": s.serper.api_key},
                              json={"q": _with_sites(query, domains), "gl": s.country, "hl": s.language,
                                    "num": s.results_per_query})
    _raise_for("serper", r)
    return [Hit(i.get("link", ""), i.get("title", ""), i.get("snippet", ""), published=_day(i.get("date")))
            for i in r.json().get("organic", [])]


async def _brave(query: str, domains: list[str] | None, config: Config) -> list[Hit]:
    s = config.search
    async with httpx.AsyncClient(timeout=s.api_timeout_seconds) as client:
        r = await client.get("https://api.search.brave.com/res/v1/web/search",
                             headers={"X-Subscription-Token": s.brave.api_key, "Accept": "application/json"},
                             params={"q": _with_sites(query, domains), "count": s.results_per_query,
                                     "country": s.country.upper(), "search_lang": s.language})
    _raise_for("brave", r)
    results = r.json().get("web", {}).get("results", [])
    return [Hit(i.get("url", ""), i.get("title", ""), i.get("description", ""), published=_day(i.get("page_age")))
            for i in results]


async def _tavily(query: str, domains: list[str] | None, config: Config) -> list[Hit]:
    s = config.search
    body: dict[str, object] = {"query": query, "max_results": s.results_per_query}
    if domains:
        body["include_domains"] = domains
    async with httpx.AsyncClient(timeout=s.api_timeout_seconds) as client:
        r = await client.post("https://api.tavily.com/search", headers={"Authorization": f"Bearer {s.tavily.api_key}"},
                              json=body)
    _raise_for("tavily", r)
    return [Hit(i.get("url", ""), i.get("title", ""), i.get("content", ""), published=_day(i.get("published_date")))
            for i in r.json().get("results", [])]


async def _selenium(engine: str, query: str, domains: list[str] | None, config: Config) -> list[Hit]:
    s = config.search
    try:
        rows = await asyncio.to_thread(browser_search.search, engine, _with_sites(query, domains),
                                       s.results_per_query, s.country, s.selenium.page_timeout_seconds)
    except browser_search.BrowserBlocked as exc:
        raise EngineFailure(str(exc)) from exc
    return [Hit(r["url"], r["title"], r["snippet"]) for r in rows]


def plan(config: Config) -> list[Attempt]:
    """Ordered attempts. Keyed providers without a key are left out (not configured isn't a failure)."""
    s = config.search
    attempts: list[Attempt] = []
    for provider in s.providers:
        if provider == "searxng":
            attempts += [Attempt(f"searxng:{e}", "searxng", partial(_searxng, e)) for e in s.searxng.engines]
        elif provider == "selenium":
            attempts += [Attempt(f"selenium:{e}", "selenium", partial(_selenium, e)) for e in s.selenium.engines]
        elif provider == "serper" and s.serper.api_key:
            attempts.append(Attempt("serper", "serper", _serper))
        elif provider == "tavily" and s.tavily.api_key:
            attempts.append(Attempt("tavily", "tavily", _tavily))
        elif provider == "brave" and s.brave.api_key:
            attempts.append(Attempt("brave", "brave", _brave))
    return attempts


_parallel: asyncio.Semaphore | None = None


def _limiter(config: Config) -> asyncio.Semaphore:
    # Few searches at a time per worker: bursts are what get engines to show CAPTCHAs.
    # Created on first use, so changing search.max_parallel needs a worker restart.
    global _parallel
    if _parallel is None:
        _parallel = asyncio.Semaphore(config.search.max_parallel)
    return _parallel


async def run_chain(query: str, domains: list[str] | None, config: Config, attempts: list[Attempt],
                    health: SearchHealth) -> list[Hit]:
    if not attempts:
        raise SearchError("No search provider is configured.")
    errors: list[str] = []
    down: set[str] = set()
    for respect_cooldowns in (True, False):  # if everything is cooling down, try anyway rather than give up
        tried = False
        for attempt in attempts:
            if attempt.provider in down:
                continue
            if respect_cooldowns and (await health.cooling_down(attempt.name)
                                      or await health.cooling_down(attempt.provider)):
                continue
            tried = True
            try:
                hits = await attempt.run(query, domains, config)
            except ProviderDown as exc:
                down.add(attempt.provider)
                errors.append(f"{attempt.provider}: {exc}")
                await health.failed(attempt.provider, str(exc))
                continue
            except Exception as exc:
                errors.append(f"{attempt.name}: {type(exc).__name__}: {exc}")
                await health.failed(attempt.name, f"{type(exc).__name__}: {exc}")
                continue
            await health.succeeded(attempt.name)
            if attempt.provider != attempt.name:
                await health.succeeded(attempt.provider)
            await health.succeeded(ALL_PROVIDERS)
            for hit in hits:
                hit.served_by = attempt.name
            log.debug("search answered", engine=attempt.name, results=len(hits))
            return hits
        if tried:
            break
    summary = " | ".join(errors)[-1000:]
    await health.failed(ALL_PROVIDERS, summary)
    raise SearchError(f"All search providers failed: {summary}")


async def web_search(query: str, include_domains: list[str] | None = None) -> list[Hit]:
    config = get_config()
    health = SearchHealth(queue_redis(), config.search.failure_cooldown_seconds)
    async with _limiter(config):
        return await run_chain(query, include_domains, config, plan(config), health)


async def factcheck_search(query: str) -> list[Hit]:
    """Existing fact-checks from Google Fact Check Tools (claims:search). Empty if not configured."""
    full = get_config()
    config = full.factcheck
    if not config.google_api_key:
        return []
    # The key goes in a header, not the query string: httpx puts the URL in error messages, which get logged.
    async with httpx.AsyncClient(timeout=full.search.api_timeout_seconds) as client:
        r = await client.get(
            "https://factchecktools.googleapis.com/v1alpha1/claims:search",
            headers={"X-Goog-Api-Key": config.google_api_key},
            params={"query": query[:500], "languageCode": config.language, "pageSize": config.max_results},
        )
    _raise_for("google-factcheck", r)
    hits: list[Hit] = []
    for claim in r.json().get("claims", []):
        for review in claim.get("claimReview", []):
            publisher = review.get("publisher", {}).get("name", "")
            snippet = f"{publisher} rated “{claim.get('text', '')[:200]}” as: {review.get('textualRating', '')}"
            hits.append(Hit(review.get("url", ""), review.get("title", "") or publisher, snippet,
                            served_by="google-factcheck", published=_day(review.get("reviewDate"))))
    return hits
