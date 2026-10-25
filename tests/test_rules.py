from datetime import UTC, datetime, timedelta

import pytest

from app.auth import issue_session, read_session
from app.config import FrameInterval, get_config
from app.models import Source
from app.pipeline.claims import ExtractedClaim, claim_id
from app.pipeline.media import evenly_spaced, frame_interval
from app.pipeline.ranking import lookup, registrable_domain
from app.pipeline.verify import enforce_rules, expiry
from app.ratelimit import parse_rule
from app.services.submissions import parse_reel_url


@pytest.mark.parametrize("url,expected", [
    ("https://www.instagram.com/reel/C8xQ2pLs/", "C8xQ2pLs"),
    ("instagram.com/reels/C8xQ2pLs?igsh=abc", "C8xQ2pLs"),
    ("https://instagram.com/someone/reel/Ab_-12345/", "Ab_-12345"),
    ("https://www.instagram.com/p/C8xQ2pLs/", "C8xQ2pLs"),
    ("https://example.com/reel/C8xQ2pLs/", None),
    ("not a url", None),
])
def test_parse_reel_url(url, expected):
    assert parse_reel_url(url) == expected


def test_rate_limit_rules():
    assert parse_rule("5/hour").limit == 5 and parse_rule("5/hour").window == 3600
    assert parse_rule("120/minutes").window == 60
    with pytest.raises(ValueError):
        parse_rule("lots/hour")


def test_frame_interval_table():
    rows = [FrameInterval(max_seconds=15, every=0.5), FrameInterval(max_seconds=60, every=1)]
    assert frame_interval(10, rows) == 0.5
    assert frame_interval(40, rows) == 1
    assert frame_interval(500, rows) == 1
    assert evenly_spaced(list(range(10)), 3) == [0, 3, 6]


def test_registrable_domain_and_ranking(config_file):
    assert registrable_domain("main.sci.gov.in") == "sci.gov.in"
    assert registrable_domain("news.example.com") == "example.com"
    rankings = {"sources": [{"domain": "gov.in", "rank": "A", "kind": "primary"},
                            {"domain": "pib.gov.in", "rank": "B", "kind": "factcheck"}]}
    assert lookup("factcheck.pib.gov.in", rankings) == {"rank": "B", "kind": "factcheck"}
    assert lookup("mha.gov.in", rankings) == {"rank": "A", "kind": "primary"}
    assert lookup("random.blog", rankings)["rank"] == "D"


def src(domain):
    return Source(url=f"https://{domain}/x", domain=domain, tier=3)


def test_true_false_need_independent_sources_with_the_right_stance():
    same_org = [(src("a.example.com"), "contradicts"), (src("b.example.com"), "contradicts")]
    assert enforce_rules("false", "x", same_org, "verifiable", 2)[0] == "unverified"
    two_orgs = [(src("example.com"), "contradicts"), (src("other.org"), "contradicts")]
    assert enforce_rules("false", "x", two_orgs, "verifiable", 2)[0] == "false"
    # Supporting sources don't count towards "false", and vice versa.
    assert enforce_rules("true", "x", two_orgs, "verifiable", 2)[0] == "unverified"


def test_related_background_never_settles_a_claim():
    """Regression: "applications must be filed 10 days ahead" was taken as proof that an application
    wasn't filed 3 days ahead. Sources about a related rule are "related", so "false" is refused."""
    rule_sources = [(src("newsonair.gov.in"), "related"), (src("thehindu.com"), "related"),
                    (src("newindianexpress.com"), "related")]
    verdict, explanation = enforce_rules("false", "Rules require 10 days.", rule_sources, "verifiable", 2)
    assert verdict == "unverified" and "directly contradict" in explanation


def test_contested_claims_never_get_true_or_false():
    two_orgs = [(src("example.com"), "supports"), (src("other.org"), "supports")]
    assert enforce_rules("true", "x", two_orgs, "contested", 2)[0] == "unverified"


def test_expiry_uses_volatility_and_prediction_dates(config_file):
    config = get_config()
    now = datetime(2026, 10, 18, tzinfo=UTC)
    breaking = ExtractedClaim(text="x", type="verifiable", volatility="breaking")
    assert expiry(breaking, now, config) == now + timedelta(hours=config.ttl.breaking_hours)
    prediction = ExtractedClaim(text="x", type="prediction", resolution_date="2026-11-01")
    assert expiry(prediction, now, config) == datetime(2026, 11, 1, tzinfo=UTC)


def test_claim_ids_ignore_case_and_punctuation():
    assert claim_id("The court banned protests.") == claim_id("the court  banned protests")


def test_session_round_trip_and_tamper(config_file):
    config = get_config()
    token, _ = issue_session("Someone@Example.com", config)
    assert read_session(token, config) == "someone@example.com"
    assert read_session(token[:-2] + "xx", config) is None
