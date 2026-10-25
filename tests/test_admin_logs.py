from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth import issue_session
from app.config import get_config
from app.logsvc.main import connect
from app.services import logs_query
from app.services.logs_query import LogFilter, ts

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
A, B = "a" * 32, "b" * 32


@pytest.fixture
def logs_db(tmp_path):
    path = tmp_path / "logs.sqlite"
    db = connect(str(path))
    rows = [
        (A, ts(NOW - timedelta(minutes=50)), "info", "[api] job queued reel_id=REEL123 job_id=j1"),
        (A, ts(NOW - timedelta(minutes=49)), "debug", "[worker] step started step=metadata"),
        (A, ts(NOW - timedelta(minutes=48)), "error", "[worker] downloader failed: 100%_sure"),
        (B, ts(NOW - timedelta(minutes=10)), "info", "[api] POST /api/v1/submissions 202 40ms"),
        ("-", ts(NOW - timedelta(minutes=5)), "info", "[worker] worker started"),
    ]
    db.executemany("INSERT INTO website_logs VALUES (?, ?, ?, ?)", rows)
    db.execute("INSERT INTO business_critical VALUES (?, ?, ?, ?, ?)",
               (ts(NOW - timedelta(minutes=20)), A, "searxng:google", "failing", "access denied"))
    db.commit()
    db.close()
    return path


def test_trace_journey_is_oldest_first_and_filterable(logs_db):
    rows = logs_query.by_traces(logs_db, [A], LogFilter())
    assert [r["log_level"] for r in rows] == ["info", "debug", "error"]
    assert len(logs_query.by_traces(logs_db, [A], LogFilter(levels=["error"]))) == 1
    assert len(logs_query.by_traces(logs_db, [A], LogFilter(sources=["api"]))) == 1


def test_reel_lookup_finds_traces_mentioning_it(logs_db):
    assert logs_query.traces_mentioning(logs_db, "REEL123") == [A]


def test_like_wildcards_in_text_are_literal(logs_db):
    assert len(logs_query.by_traces(logs_db, [A], LogFilter(text="100%_sure"))) == 1
    assert len(logs_query.by_traces(logs_db, [A], LogFilter(text="100%x"))) == 0


def test_range_is_newest_first_and_pages(logs_db):
    window = LogFilter(since=NOW - timedelta(hours=1))
    first = logs_query.by_range(logs_db, window, limit=2, before=None)
    assert [r["trace_id"] for r in first["items"]] == ["-", B] and first["next_before"]
    rest = logs_query.by_range(logs_db, window, limit=10, before=first["next_before"])
    assert len(rest["items"]) == 3 and rest["next_before"] is None
    recent = logs_query.by_range(logs_db, LogFilter(since=NOW - timedelta(minutes=15)), 10, None)
    assert len(recent["items"]) == 2


def test_business_critical_and_missing_file(logs_db, tmp_path):
    assert logs_query.business_critical(logs_db, NOW - timedelta(hours=1), None, 10)[0]["event"] == "failing"
    missing = tmp_path / "nope.sqlite"
    assert logs_query.by_range(missing, LogFilter(), 10, None) == {"items": [], "next_before": None}


def test_admin_endpoints_are_hidden_from_everyone_else(config_file, edit_config, logs_db, monkeypatch):
    edit_config(lambda d: (d["auth"].update(admins=["boss@example.org"]),
                           d["logging"].update(sqlite_path=str(logs_db))))

    async def no_limit(*_args):
        return 0

    monkeypatch.setattr("app.api.deps.hit", no_limit)  # no Redis in the test container
    from main import app

    config = get_config()
    cookie = config.auth.jwt.cookie_name

    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/admin/logs").status_code == 404

    invited = TestClient(app, cookies={cookie: issue_session(config.auth.invited.mail[0], config)[0]})
    assert invited.get("/api/v1/admin/logs").status_code == 404

    admin = TestClient(app, cookies={cookie: issue_session("Boss@Example.org", config)[0]})
    response = admin.get(f"/api/v1/admin/logs?trace_id={A}")
    assert response.status_code == 200 and len(response.json()["items"]) == 3
    me = admin.get("/api/v1/auth/me").json()
    assert me["is_admin"] and me["invited"]
