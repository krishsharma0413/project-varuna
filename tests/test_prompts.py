from datetime import UTC, datetime

import pytest
import yaml

from app.models import Source
from app.pipeline import llm, prompts, verify
from app.pipeline.claims import ExtractedClaim
from app.pipeline.prompts import REPO_FILE, PromptsError, parse
from app.pipeline.verify import SourceStance, VerdictOut, new_queries

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


def _raw() -> dict:
    return yaml.safe_load(REPO_FILE.read_text(encoding="utf-8"))


def test_repo_prompts_are_valid_and_versioned():
    loaded = parse(REPO_FILE.read_text(encoding="utf-8"))
    assert loaded.version.startswith(f"{_raw()['version']}+")
    assert "{evidence}" in loaded.texts["verdict"]
    assert "Iran" in loaded.render("verdict", today="", claim="c", claim_type="verifiable", delivery="literal",
                                   context="", evidence="(none)", research="", min_sources=2)


@pytest.mark.parametrize("change, problem", [
    (lambda d: d.update(verdict=d["verdict"].replace("{evidence}", "")), "missing placeholders evidence"),
    (lambda d: d.update(claims=d["claims"] + " {secret}"), "unknown placeholders secret"),
    (lambda d: d.update(ocr="Return { here"), "bad braces"),
    (lambda d: d.pop("cleanup"), "cleanup: missing"),
    (lambda d: d.update(extra="x"), "unknown keys: extra"),
])
def test_invalid_prompts_are_rejected(change, problem):
    data = _raw()
    change(data)
    with pytest.raises(PromptsError, match=problem):
        parse(yaml.safe_dump(data, allow_unicode=True))


def test_editing_without_a_version_bump_still_changes_the_version():
    data = _raw()
    first = parse(yaml.safe_dump(data, allow_unicode=True)).version
    data["ocr"] += " Also read watermarks."
    assert parse(yaml.safe_dump(data, allow_unicode=True)).version != first


def test_a_broken_file_keeps_the_last_good_prompts(tmp_path, monkeypatch):
    path = tmp_path / "prompts.yaml"
    path.write_text(REPO_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(prompts, "prompts_path", lambda: path)
    good = prompts.get()
    path.write_text("verdict: {claim", encoding="utf-8")
    assert prompts.get() == good


def test_follow_up_queries_skip_repeats_and_blanks():
    searched = ["Jantar Mantar protest permission Delhi"]
    proposed = ["jantar mantar protest, permission delhi!", "  ", "Delhi Police permission letter date", "x", "y"]
    assert new_queries(proposed, searched, 2) == ["Delhi Police permission letter date", "x"]


def _src(n: int) -> Source:
    return Source(url=f"https://news{n}.example/a", domain=f"news{n}.example", tier=3)


@pytest.fixture
def research(config_file, monkeypatch):
    """verify.decide with fake search and a scripted model. Returns (answers, calls, searches)."""
    answers: list[VerdictOut] = []
    calls: list[str] = []
    searches: list[list[str]] = []

    async def gather(claim, config):
        return [_src(0), _src(1)]

    async def follow_up(queries, known, round_no, config):
        searches.append(queries)
        return [_src(10 * round_no + i) for i in range(len(queries))]

    async def chat_json(model, messages, schema, temperature=0.1, reasoning="default"):
        calls.append(messages[0]["content"])
        return answers[len(calls) - 1]

    monkeypatch.setattr(verify, "gather_evidence", gather)
    monkeypatch.setattr(verify, "follow_up_evidence", follow_up)
    monkeypatch.setattr(llm, "chat_json", chat_json)
    return answers, calls, searches


CLAIM = ExtractedClaim(text="The group filed its protest application three days before the protest.",
                       type="verifiable", search_queries=["protest application Jantar Mantar"])


def _answer(verdict="unverified", follow=(), sources=()):
    return VerdictOut(assertion="a", sources=[SourceStance(id=i, stance="supports") for i in sources],
                      verdict=verdict, explanation="e", follow_up_queries=list(follow))


async def test_research_stops_at_max_rounds(research):
    answers, calls, searches = research
    answers += [_answer(follow=["q1"]), _answer(follow=["q2"]), _answer(verdict="true", follow=["q3"], sources=[2, 3])]
    decision, evidence, searched, rounds = await verify.decide(CLAIM, "", prompts_config(), NOW)
    assert rounds == 3 and len(calls) == 3 and searches == [["q1"], ["q2"]]
    assert searched == ["protest application Jantar Mantar", "q1", "q2"]
    assert len(evidence) == 4 and decision.verdict == "true"
    assert "round 1 of 3" in calls[0] and "final round (3 of 3)" in calls[2]


async def test_research_stops_when_the_model_is_satisfied(research):
    answers, calls, searches = research
    answers.append(_answer(verdict="false", sources=[0, 1]))
    _, _, _, rounds = await verify.decide(CLAIM, "", prompts_config(), NOW)
    assert rounds == 1 and len(calls) == 1 and searches == []


async def test_one_round_means_no_follow_ups(research, edit_config):
    edit_config(lambda d: d["verification"].update(research={"max_rounds": 1}))
    answers, calls, searches = research
    answers.append(_answer(follow=["more"]))
    _, _, _, rounds = await verify.decide(CLAIM, "", prompts_config(), NOW)
    assert rounds == 1 and searches == [] and "final round (1 of 1)" in calls[0]


def prompts_config():
    from app.config import get_config

    return get_config()


def test_publication_dates_become_absolute():
    from datetime import date

    from app.pipeline.search import _day

    today = date(2026, 10, 18)
    assert _day("6 days ago", today) == "2026-10-12"
    assert _day("1 week ago", today) == "2026-10-11"
    assert _day("an hour ago", today) == "2026-10-18"
    assert _day("2026-10-09T08:00:00Z", today) == "2026-10-09"
    assert _day("9 Oct 2026", today) == "9 Oct 2026"
    assert _day(None, today) == ""
