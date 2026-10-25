from datetime import UTC, datetime, timedelta

from app.config import get_config
from app.pipeline import llm, topic_gate
from app.pipeline.topic_gate import GateDecision, is_remembered_rejection, match_topics, topics_hash

NOW = datetime(2026, 10, 18, tzinfo=UTC)


def fake_model(monkeypatch, answer: GateDecision, calls: list):
    async def chat_json(model, messages, schema, temperature=0.1, reasoning="default"):
        calls.append(messages[0]["content"])
        return answer

    monkeypatch.setattr(llm, "chat_json", chat_json)


async def test_on_topic_caption_passes_with_canonical_topic_names(config_file, monkeypatch):
    calls = []
    answer = GateDecision(relevant=True, matched_topics=["delhi protests"], reason="About protests.")
    fake_model(monkeypatch, answer, calls)
    decision = await topic_gate.check("Police at Jantar Mantar today #delhiprotest", get_config())
    assert decision.relevant and decision.matched_topics == ["Delhi protests"]
    assert "Jantar Mantar" in calls[0] and "- UGC bill" in calls[0]


async def test_off_topic_caption_is_rejected(config_file, monkeypatch):
    fake_model(monkeypatch, GateDecision(relevant=False, matched_topics=["Health"], reason="A dance trend."), [])
    decision = await topic_gate.check("POV: when the beat drops 💃 #trending", get_config())
    assert not decision.relevant and decision.matched_topics == []


async def test_relevant_without_a_listed_topic_is_rejected(config_file, monkeypatch):
    fake_model(monkeypatch, GateDecision(relevant=True, matched_topics=["Cricket"], reason="Sports."), [])
    decision = await topic_gate.check("Big match tonight", get_config())
    assert not decision.relevant


async def test_empty_caption_follows_config_without_calling_the_model(edit_config, monkeypatch):
    calls = []
    fake_model(monkeypatch, GateDecision(relevant=True, reason="ok"), calls)
    assert not (await topic_gate.check("   ", get_config())).relevant
    edit_config(lambda d: d["topic_gate"].update(empty_caption="allow"))
    assert (await topic_gate.check("", get_config())).relevant
    assert calls == []


async def test_disabled_gate_lets_everything_through(edit_config, monkeypatch):
    calls = []
    fake_model(monkeypatch, GateDecision(relevant=False, reason="no"), calls)
    edit_config(lambda d: d["topic_gate"].update(enabled=False))
    assert (await topic_gate.check("anything", get_config())).relevant and calls == []


def test_topic_matching_and_hash():
    topics = ["Delhi protests", "UGC bill"]
    assert match_topics(["ugc bill", "the Delhi protests"], topics) == ["Delhi protests", "UGC bill"]
    assert topics_hash(["UGC bill", "Delhi protests"]) == topics_hash([" delhi protests", "ugc bill"])
    assert topics_hash(topics) != topics_hash([*topics, "Elections"])


def test_remembered_rejection_expires_and_resets_when_topics_change(config_file):
    config = get_config()
    gate = {"relevant": False, "topics_hash": topics_hash(config.topics), "checked_at": NOW - timedelta(hours=1)}
    assert is_remembered_rejection(gate, config, NOW)
    assert not is_remembered_rejection({**gate, "relevant": True}, config, NOW)
    assert not is_remembered_rejection({**gate, "topics_hash": "old"}, config, NOW)
    old = NOW - timedelta(hours=config.topic_gate.remember_hours + 1)
    assert not is_remembered_rejection({**gate, "checked_at": old}, config, NOW)


def test_gate_needs_a_reason_and_falls_back_to_a_default():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GateDecision(relevant=False, reason="")


async def test_whitespace_reason_gets_default(config_file, monkeypatch):
    fake_model(monkeypatch, GateDecision(relevant=False, reason="   "), [])
    decision = await topic_gate.check("some caption", get_config())
    assert decision.reason == topic_gate.DEFAULT_REJECTION


def test_ytdlp_handle_prefers_username_over_numeric_id():
    from app.pipeline.download import ytdlp_handle

    info = {"channel": "Some.User", "uploader_id": "78535471288", "uploader": "Display Name"}
    assert ytdlp_handle(info) == "some.user"
    assert ytdlp_handle({"uploader_id": "78535471288", "uploader": "Display Name"}) == ""
    assert ytdlp_handle({"uploader_id": "@named_user"}) == "named_user"
