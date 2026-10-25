from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.auth import issue_session
from app.config import get_config
from app.services.admin_records import plan, row

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


def _reel(**extra):
    return {
        "_id": "REEL1",
        "creator_handle": "someone",
        "current": {
            "claims": [{"claim_id": "c1", "verdict": "false"}, {"claim_id": "c2", "verdict": "true"}],
            "checked_at": NOW, "expires_at": NOW + timedelta(hours=1), "summary": {"verdict": "false"},
        },
        "history": [{"claims": []}],
        **extra,
    }


def test_plan_deletes_own_claims_expires_shared_and_undoes_creator_counts():
    claims = [{"_id": "c1", "reel_ids": ["REEL1"]}, {"_id": "c2", "reel_ids": ["REEL1", "OTHER"]}]
    changes = plan(_reel(), claims)
    assert changes["delete_claims"] == ["c1"]
    assert changes["expire_shared_claims"] == ["c2"]
    assert changes["creator"] == "someone"
    assert changes["creator_inc"] == {
        "counts.false": -1, "counts.true": -1, "claims_checked": -2, "reels_checked": -1,
    }
    assert changes["history_entries"] == 1


def test_plan_without_a_result_leaves_the_creator_alone():
    changes = plan({"_id": "REEL1", "creator_handle": "someone", "current": None,
                    "gate": {"relevant": False}}, [])
    assert changes["creator"] is None and changes["creator_inc"] == {}


def test_row_states():
    assert row(_reel(), NOW)["state"] == "checked"
    assert row(_reel(), NOW + timedelta(hours=2))["state"] == "stale"
    rejected = row({"_id": "R", "current": None, "gate": {"relevant": False, "reason": "Off topic.",
                                                          "checked_at": NOW}}, NOW)
    assert rejected["state"] == "rejected" and rejected["gate_reason"] == "Off topic."
    assert rejected["last_activity"] == NOW
    assert row({"_id": "R", "current": None}, NOW)["state"] == "empty"


def test_record_endpoints_are_hidden_from_everyone_else(config_file, edit_config, monkeypatch):
    edit_config(lambda d: d["auth"].update(admins=["boss@example.org"]))

    async def no_limit(*_args):
        return 0

    monkeypatch.setattr("app.api.deps.hit", no_limit)  # no Redis in the test container
    from main import app

    config = get_config()
    cookie = config.auth.jwt.cookie_name
    invited = TestClient(app, cookies={cookie: issue_session(config.auth.invited.mail[0], config)[0]})
    for client in (TestClient(app), invited):
        assert client.get("/api/v1/admin/reels").status_code == 404
        assert client.delete("/api/v1/admin/reels/REEL1").status_code == 404
