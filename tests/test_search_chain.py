import base64

import httpx
import pytest

from app.config import get_config
from app.log import log
from app.pipeline.browser_search import real_url
from app.pipeline.search import (
    Attempt,
    EngineFailure,
    Hit,
    ProviderDown,
    SearchError,
    factcheck_search,
    plan,
    run_chain,
)
from app.pipeline.search_health import ALL_PROVIDERS, SearchHealth


class FakeStore:
    """In-memory stand-in for the queue Redis (exists/set/delete with get=)."""

    def __init__(self):
        self.data = {}

    async def exists(self, *names):
        return sum(n in self.data for n in names)

    async def set(self, name, value, ex=None, get=False):
        previous = self.data.get(name)
        self.data[name] = value
        return previous if get else True

    async def delete(self, *names):
        return sum(self.data.pop(n, None) is not None for n in names)


def ok(*urls):
    async def run(query, domains, config):
        return [Hit(u, "t", "s") for u in urls]
    return run


def fails(exc):
    async def run(query, domains, config):
        raise exc
    return run


@pytest.fixture
def critical():
    log._critical.clear()
    yield log._critical
    log._critical.clear()


async def test_falls_through_in_order_and_records_first_failure_only(config_file, critical):
    config, store = get_config(), FakeStore()
    health = SearchHealth(store, cooldown_seconds=600)
    attempts = [
        Attempt("searxng:google", "searxng", fails(EngineFailure("google: access denied"))),
        Attempt("searxng:duckduckgo", "searxng", ok("https://a.example/1")),
        Attempt("serper", "serper", ok("https://never.example")),
    ]
    hits = await run_chain("q", None, config, attempts, health)
    assert [h.url for h in hits] == ["https://a.example/1"] and hits[0].served_by == "searxng:duckduckgo"
    assert [(c["search_engine"], c["event"]) for c in critical] == [("searxng:google", "failing")]

    # google is cooling down now, so it isn't even tried, and nothing new is recorded
    attempts[0] = Attempt("searxng:google", "searxng", fails(AssertionError("should be skipped")))
    await run_chain("q", None, config, attempts, health)
    assert len(critical) == 1


async def test_recovery_is_recorded_once(config_file, critical):
    config, store = get_config(), FakeStore()
    health = SearchHealth(store, cooldown_seconds=0)  # no cooldown, so the engine is retried at once
    flaky = [Attempt("serper", "serper", fails(EngineFailure("HTTP 400: not enough credits")))]
    with pytest.raises(SearchError):
        await run_chain("q", None, config, flaky, health)
    await run_chain("q", None, config, [Attempt("serper", "serper", ok("https://b.example"))], health)
    await run_chain("q", None, config, [Attempt("serper", "serper", ok("https://b.example"))], health)
    events = [(c["search_engine"], c["event"]) for c in critical]
    assert events == [("serper", "failing"), (ALL_PROVIDERS, "failing"), ("serper", "recovered"),
                      (ALL_PROVIDERS, "recovered")]


async def test_provider_down_skips_its_other_engines(config_file, critical):
    config = get_config()
    health = SearchHealth(FakeStore(), cooldown_seconds=600)
    attempts = [
        Attempt("searxng:google", "searxng", fails(ProviderDown("SearXNG unreachable"))),
        Attempt("searxng:duckduckgo", "searxng", fails(AssertionError("should be skipped"))),
        Attempt("selenium:duckduckgo", "selenium", ok("https://c.example")),
    ]
    hits = await run_chain("q", None, config, attempts, health)
    assert hits[0].served_by == "selenium:duckduckgo"
    assert [(c["search_engine"], c["event"]) for c in critical] == [("searxng", "failing")]


async def test_when_everything_is_cooling_down_it_still_tries(config_file, critical):
    config, store = get_config(), FakeStore()
    store.data["search:cooldown:serper"] = "1"
    hits = await run_chain("q", None, config, [Attempt("serper", "serper", ok("https://d.example"))],
                           SearchHealth(store, 600))
    assert hits[0].url == "https://d.example"


def test_plan_order_and_unkeyed_providers_skipped(edit_config):
    edit_config(lambda d: d["search"].update(providers=["searxng", "serper", "selenium"],
                                             serper={"api_key": ""}))
    config = get_config()
    names = [a.name for a in plan(config)]
    assert names[0] == "searxng:google" and "serper" not in names
    assert names[-len(config.search.selenium.engines):] == [f"selenium:{e}" for e in config.search.selenium.engines]


async def test_factcheck_key_goes_in_a_header_never_the_url(edit_config, monkeypatch):
    """httpx puts the request URL in error messages, which are logged; the API key must not be in it."""
    edit_config(lambda d: d["factcheck"].update(google_api_key="AIza-SECRET-KEY"))
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(403, json={"error": {"message": "API key not valid"}})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    with pytest.raises(EngineFailure) as failure:
        await factcheck_search("a claim")
    assert seen[0].headers["x-goog-api-key"] == "AIza-SECRET-KEY"
    assert "SECRET" not in str(seen[0].url) and "SECRET" not in str(failure.value)


def test_redirect_wrappers_are_unwrapped():
    assert real_url("https://duckduckgo.com/l/?uddg=https%3A%2F%2Fsci.gov.in%2Forder&rut=x") == "https://sci.gov.in/order"
    encoded = base64.urlsafe_b64encode(b"https://pib.gov.in/fact").decode().rstrip("=")
    assert real_url(f"https://www.bing.com/ck/a?!&&p=abc&u=a1{encoded}&ntb=1") == "https://pib.gov.in/fact"
    assert real_url("https://example.org/x") == "https://example.org/x"
