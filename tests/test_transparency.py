import json

from app.config import get_config
from app.pipeline import extract, llm
from app.services import transparency

SECRETS = {
    "openrouter.api_key": "sk-or-SECRET-123",
    "search.serper.api_key": "serper-SECRET-456",
    "search.tavily.api_key": "tavily-SECRET-456",
    "search.brave.api_key": "brave-SECRET-456",
    "factcheck.google_api_key": "google-SECRET-789",
    "downloader.instaloader.username": "burner_SECRET_user",
    "downloader.instaloader.password": "pw-SECRET-000",
    "auth.jwt.secret": "jwt-SECRET-" + "x" * 40,
    "auth.google.client_id": "client-SECRET.apps.googleusercontent.com",
    "auth.google.client_secret": "GOCSPX-SECRET",
    "mongo.uri": "mongodb://user:SECRET@host/db",
}


def _set(data, dotted, value):
    *path, last = dotted.split(".")
    for key in path:
        data = data[key]
    data[last] = value


def test_transparency_never_exposes_secrets_or_invites(edit_config):
    edit_config(lambda d: [_set(d, k, v) for k, v in SECRETS.items()])
    payload = json.dumps(transparency.build(get_config()))
    assert "SECRET" not in payload
    assert "xyz.com" not in payload and "instagram_handle" not in payload


def test_transparency_lists_models_from_config(config_file):
    config = get_config()
    payload = transparency.build(config)
    slugs = {m["role"]: m["slug"] for m in payload["models"]}
    assert slugs["transcription"] == config.openrouter.models.transcription
    assert slugs["strong"] == config.openrouter.models.strong
    urls = {m["role"]: m["url"] for m in payload["models"]}
    assert urls["transcription"] == f"https://openrouter.ai/{config.openrouter.models.transcription}"
    assert slugs["gate"] == config.openrouter.models.small and payload["topic_gate"]["topics"] == config.topics
    assert {p["name"] for p in payload["prompts"]} >= {"Topic check", "Claim extraction", "Verdict"}


async def test_stt_mode_calls_transcription_endpoint(config_file, tmp_path, monkeypatch):
    calls = []

    async def fake_post(path, body):
        calls.append((path, body))
        return {"text": " namaste ", "usage": {"seconds": 9.2, "cost": 0.0005}}

    monkeypatch.setattr(llm, "_post", fake_post)
    chunk = tmp_path / "chunk_000.mp3"
    chunk.write_bytes(b"ID3fake")
    text = await extract.transcribe([chunk], get_config())
    assert text == "namaste"
    path, body = calls[0]
    assert path == "/audio/transcriptions"
    assert body["model"] == get_config().openrouter.models.transcription
    assert body["input_audio"]["format"] == "mp3" and "language" not in body
