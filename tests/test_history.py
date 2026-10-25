from datetime import UTC, datetime

from app.models import ClaimResult
from app.services.history import archive_entry, creator_delta, history_push, summarize

NOW = datetime(2026, 10, 18, tzinfo=UTC)


def claim(text, verdict):
    return ClaimResult(claim_id=text, text=text, type="verifiable", volatility="ongoing", verdict=verdict,
                       explanation="", checked_at=NOW, expires_at=NOW)


def test_summary_headlines_most_severe_verdict():
    summary = summarize([claim("a", "true"), claim("b", "false"), claim("c", "unverified")])
    assert summary.verdict == "false"
    assert summary.claim_text == "b"
    assert summary.counts["true"] == 1 and summary.claim_count == 3


def test_archive_strips_raw_text_unless_configured():
    result = {"claims": [], "extraction": {"transcript": "t", "ocr_text": "o", "caption": "c", "cleaned_text": "x"}}
    assert archive_entry(result, keep_raw_text=False)["extraction"] == {"cleaned_text": "x"}
    assert archive_entry(result, keep_raw_text=True)["extraction"]["transcript"] == "t"
    assert result["extraction"]["transcript"] == "t"  # original untouched


def test_history_push_caps_only_when_configured():
    assert history_push({"a": 1}, 0) == {"$each": [{"a": 1}]}
    assert history_push({"a": 1}, 10) == {"$each": [{"a": 1}], "$slice": -10}


def test_creator_delta_replaces_old_counts():
    old = {"claims": [{"verdict": "false"}, {"verdict": "true"}]}
    new = {"claims": [{"verdict": "true"}, {"verdict": "true"}, {"verdict": "misleading"}]}
    assert creator_delta(None, old) == {"counts.true": 1, "counts.false": 1, "claims_checked": 2, "reels_checked": 1}
    assert creator_delta(old, new) == {"counts.true": 1, "counts.false": -1, "counts.misleading": 1,
                                       "claims_checked": 1}
