import json

import httpx
import pytest

from app.pipeline import llm

# What Alibaba/Qwen actually returned for reel DejgwIVSbpG: HTTP 200, no content, finish_reason "error".
PROVIDER_FAILURE = {
    "provider": "Alibaba",
    "choices": [{"finish_reason": "error", "native_finish_reason": None,
                 "message": {"role": "assistant", "content": None, "reasoning": "Frame 1: ..."}}],
}
GOOD = {"choices": [{"finish_reason": "stop", "message": {"content": "Exposing whole CJP with proofs"}}]}


@pytest.fixture(autouse=True)
def setup(config_file, edit_config, monkeypatch):
    edit_config(lambda d: d["openrouter"].update(api_key="sk-test"))

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(llm.asyncio, "sleep", no_sleep)
    yield
    llm._transport = None


def replay(*responses):
    """Mock OpenRouter answering with `responses` in order; returns the list of request bodies seen."""
    seen: list[dict] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=queue.pop(0))

    llm._transport = httpx.MockTransport(handler)
    return seen


def test_unusable_completion_cases():
    assert llm.unusable_completion(PROVIDER_FAILURE)[1] is True
    assert llm.unusable_completion(GOOD) == (None, False)
    assert llm.unusable_completion({"choices": []}) == ("the response has no choices", True)
    out_of_tokens = {"choices": [{"finish_reason": "length", "message": {"content": None}}]}
    assert llm.unusable_completion(out_of_tokens)[1] is True
    # An empty answer that finished normally is legitimate (e.g. no text on screen).
    empty_answer = {"choices": [{"finish_reason": "stop", "message": {"content": ""}}]}
    assert llm.unusable_completion(empty_answer) == (None, False)


async def test_provider_failure_is_retried_not_passed_on_as_empty():
    seen = replay(PROVIDER_FAILURE, GOOD)
    text = await llm.chat("qwen/qwen3.7-flash", [{"role": "user", "content": "read"}])
    assert text == "Exposing whole CJP with proofs" and len(seen) == 2


async def test_persistent_provider_failure_raises():
    replay(PROVIDER_FAILURE, PROVIDER_FAILURE, PROVIDER_FAILURE)
    with pytest.raises(llm.LLMError, match="failed mid-generation"):
        await llm.chat("qwen/qwen3.7-flash", [{"role": "user", "content": "read"}])


async def test_running_out_of_tokens_is_retried():
    out_of_tokens = {"choices": [{"finish_reason": "length", "message": {"content": None}}]}
    seen = replay(out_of_tokens, GOOD)
    assert await llm.chat("m", [{"role": "user", "content": "x"}]) == "Exposing whole CJP with proofs"
    assert len(seen) == 2


async def test_reasoning_effort_is_sent_only_when_set():
    seen = replay(GOOD, GOOD)
    await llm.chat("m", [{"role": "user", "content": "x"}], reasoning="none")
    await llm.chat("m", [{"role": "user", "content": "x"}])
    assert seen[0]["reasoning"] == {"effort": "none"} and "reasoning" not in seen[1]


def test_schema_sent_to_the_model_requires_every_field():
    from app.pipeline.claims import ClaimList
    from app.pipeline.llm import strict_schema

    schema = strict_schema(ClaimList.model_json_schema())
    claim = schema["$defs"]["ExtractedClaim"]
    assert set(claim["required"]) == set(claim["properties"]) >= {"search_queries", "delivery", "topic_tags"}
    assert all("default" not in p for p in claim["properties"].values())
    # validation still fills in defaults if a model leaves something out
    assert ClaimList.model_validate({"claims": [{"text": "t", "type": "opinion"}]}).claims[0].delivery == "literal"
