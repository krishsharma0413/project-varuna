import json

import httpx
import pytest

from app.log import log
from app.pipeline import llm
from app.trace import trace_id_var


@pytest.fixture
def captured():
    log._buffer.clear()
    yield log._buffer
    log._buffer.clear()


def openrouter(handler):
    llm._transport = httpx.MockTransport(handler)
    return llm


@pytest.fixture(autouse=True)
def reset_transport():
    yield
    llm._transport = None


async def test_chat_request_and_response_are_logged_with_trace(config_file, edit_config, captured):
    edit_config(lambda d: d["openrouter"].update(api_key="sk-test"))
    reply = {"id": "gen-1", "choices": [{"message": {"content": "the answer"}}], "usage": {"total_tokens": 12}}
    openrouter(lambda request: httpx.Response(200, json=reply))
    trace_id_var.set("trace-abc")

    text = await llm.chat("some/model", [{"role": "user", "content": "Is the sky green? Context: ..."}])

    assert text == "the answer"
    lines = [e for e in captured if "llm " in e["message"]]
    assert [line["trace_id"] for line in lines] == ["trace-abc", "trace-abc"]
    request, response = lines[0]["message"], lines[1]["message"]
    assert "llm request POST /chat/completions model=some/model" in request and "Is the sky green?" in request
    assert "status=200" in response and '"total_tokens":12' in response and "the answer" in response
    assert all(line["log_level"] == "info" for line in lines)
    assert "sk-test" not in request + response


async def test_images_and_audio_are_not_logged_but_responses_are(config_file, edit_config, captured):
    edit_config(lambda d: d["openrouter"].update(api_key="sk-test"))
    openrouter(lambda request: httpx.Response(200, json={"choices": [{"message": {"content": "SIGN: STOP"}}]}))
    image = "data:image/jpeg;base64," + "A" * 5000
    await llm.chat("vision/model", [{"role": "user", "content": [
        {"type": "text", "text": "Read the text"}, {"type": "image_url", "image_url": {"url": image}}]}])
    request = next(e["message"] for e in captured if "llm request" in e["message"])
    assert "Read the text" in request and "[image omitted]" in request and "AAAA" not in request
    assert any("SIGN: STOP" in e["message"] for e in captured if "llm response" in e["message"])

    captured.clear()
    openrouter(lambda request: httpx.Response(200, json={"text": "namaste", "usage": {"seconds": 3}}))
    text, _ = await llm.speech_to_text("openai/whisper", "B" * 4000, "mp3")
    request = next(e["message"] for e in captured if "llm request" in e["message"])
    assert "[audio omitted, 4000 base64 chars]" in request and "BBBB" not in request
    assert text == "namaste" and any("namaste" in e["message"] for e in captured if "llm response" in e["message"])


async def test_errors_and_embeddings(config_file, edit_config, captured):
    edit_config(lambda d: d["openrouter"].update(api_key="sk-test"))
    openrouter(lambda request: httpx.Response(400, json={"error": {"message": "bad model"}}))
    with pytest.raises(llm.LLMError):
        await llm.chat("bad/model", [{"role": "user", "content": "hi"}])
    error = next(e for e in captured if "llm response" in e["message"])
    assert error["log_level"] == "error" and "bad model" in error["message"]

    captured.clear()
    openrouter(lambda request: httpx.Response(200, json={"data": [{"embedding": [0.1] * 1536}]}))
    assert len(await llm.embed("embed/model", "text")) == 1536
    response = next(e["message"] for e in captured if "llm response" in e["message"])
    assert "[1536 floats omitted]" in response and "0.1,0.1" not in response


def test_loggable_request_leaves_the_real_body_untouched():
    body = {"model": "m", "input_audio": {"data": "xyz", "format": "mp3"}}
    assert llm.loggable_request(body)["input_audio"]["data"].startswith("[audio omitted")
    assert body["input_audio"]["data"] == "xyz"
    assert json.loads(llm._json(body))["input_audio"]["data"] == "xyz"
