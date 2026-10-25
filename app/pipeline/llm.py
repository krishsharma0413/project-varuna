"""OpenRouter client (OpenAI-compatible chat completions and embeddings) over HTTPX.

Every call is logged with the current trace ID: the full request body (image and audio data replaced
by placeholders) and the full response body (embedding vectors replaced by their length).
"""

from __future__ import annotations

import asyncio
import copy
import json
import re
import time
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_config
from app.log import log

RETRY_STATUS = {408, 429, 500, 502, 503, 504}
_transport: httpx.AsyncBaseTransport | None = None  # tests swap in a mock transport


class LLMError(Exception):
    pass


class _Retryable(LLMError):
    pass


def _headers() -> dict[str, str]:
    config = get_config()
    if not config.openrouter.api_key:
        raise LLMError("openrouter.api_key is empty in config.yaml.")
    return {
        "Authorization": f"Bearer {config.openrouter.api_key}",
        "HTTP-Referer": config.app.public_base_url,
        "X-Title": "varuna fact checker",
    }


def loggable_request(body: dict[str, Any]) -> dict[str, Any]:
    """The request body with image and audio data replaced by placeholders (text kept in full)."""
    safe = copy.deepcopy(body)
    if isinstance(safe.get("input_audio"), dict) and "data" in safe["input_audio"]:  # speech-to-text endpoint
        safe["input_audio"]["data"] = f"[audio omitted, {len(body['input_audio']['data'])} base64 chars]"
    for message in safe.get("messages", []):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if part.get("type") == "image_url":
                part["image_url"] = "[image omitted]"
            elif part.get("type") == "input_audio":
                part["input_audio"] = "[audio omitted]"
    return safe


def loggable_response(data: Any) -> Any:
    """The response body with embedding vectors replaced by their length."""
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        safe = copy.deepcopy(data)
        for item in safe["data"]:
            if isinstance(item, dict) and isinstance(item.get("embedding"), list):
                item["embedding"] = f"[{len(item['embedding'])} floats omitted]"
        return safe
    return data


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


async def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    config = get_config()
    url = config.openrouter.base_url.rstrip("/") + path
    attempts = config.openrouter.max_attempts
    model = body.get("model", "?")
    last_error: Exception | None = None
    log.info(f"llm request POST {path} model={model} body={_json(loggable_request(body))}")
    async with httpx.AsyncClient(timeout=config.openrouter.timeout_seconds, transport=_transport) as client:
        for attempt in range(attempts):
            started = time.perf_counter()
            try:
                response = await client.post(url, headers=_headers(), json=body)
                elapsed = round((time.perf_counter() - started) * 1000)
                try:
                    shown = _json(loggable_response(response.json()))
                except ValueError:
                    shown = response.text
                line = (f"llm response POST {path} model={model} status={response.status_code} "
                        f"attempt={attempt + 1} {elapsed}ms body={shown}")
                (log.error if response.status_code >= 400 else log.info)(line)
                if response.status_code in RETRY_STATUS:
                    raise _Retryable(f"OpenRouter returned {response.status_code}: {response.text[:300]}")
                if response.status_code >= 400:
                    raise LLMError(f"OpenRouter returned {response.status_code}: {response.text[:500]}")
                data = response.json()
                if "error" in data:
                    raise LLMError(f"OpenRouter error: {data['error']}")
                if path == "/chat/completions":
                    problem, retryable = unusable_completion(data)
                    if problem:
                        log.error(f"llm response POST {path} model={model} attempt={attempt + 1} unusable: {problem}")
                        raise (_Retryable if retryable else LLMError)(f"{model}: {problem}")
                return data
            except httpx.TransportError as exc:
                log.error(f"llm response POST {path} model={model} attempt={attempt + 1} "
                          f"no response: {type(exc).__name__}: {exc}")
                last_error = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(2 * 3**attempt)
            except _Retryable as exc:
                last_error = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(2 * 3**attempt)
    raise LLMError(str(last_error))


def unusable_completion(data: dict[str, Any]) -> tuple[str | None, bool]:
    """Why an HTTP-200 chat completion can't be used, and whether retrying could help.

    A provider can fail mid-generation and still answer 200 with finish_reason "error" and no content;
    passing that along as an empty answer would silently drop a step's output.
    """
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return "the response has no choices", True
    choice = choices[0] if isinstance(choices[0], dict) else {}
    finish = choice.get("finish_reason")
    content = (choice.get("message") or {}).get("content")
    if finish == "error":
        detail = (choice.get("error") or {}).get("message") or choice.get("native_finish_reason") or "no detail"
        return f"the provider failed mid-generation ({detail})", True
    if content is None or content == []:
        if finish == "length":  # usually reasoning that ran on; a fresh try normally answers
            return "it ran out of tokens before answering (reasoning may have used them all)", True
        if finish != "stop":
            return f"no content (finish_reason={finish})", True
    return None, False


def reasoning_option(effort: str) -> dict[str, Any] | None:
    """OpenRouter's `reasoning` request field for an effort setting ("default" sends nothing)."""
    return None if effort == "default" else {"effort": effort}


def provider_routing() -> dict[str, Any]:
    """OpenRouter's `provider` request field from openrouter.provider in config.yaml."""
    routing = get_config().openrouter.provider
    option: dict[str, Any] = {"require_parameters": routing.require_parameters}
    if routing.ignore:
        option["ignore"] = list(routing.ignore)
    return option


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The JSON Schema sent to the model, with every property required. Pydantic defaults leave fields
    optional, and some providers then return the bare minimum (one claim with three fields instead of
    six full claims). The defaults still apply when validating, so this only changes what's asked for."""
    def visit(node: Any) -> Any:
        if isinstance(node, dict):
            node = {k: visit(v) for k, v in node.items()}
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["required"] = list(node["properties"])
                for prop in node["properties"].values():
                    prop.pop("default", None)
            return node
        if isinstance(node, list):
            return [visit(v) for v in node]
        return node

    return visit(schema)


def _content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected OpenRouter response: {str(data)[:300]}") from exc
    if isinstance(content, list):  # some providers return content parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content or ""


async def chat(model: str, messages: list[dict[str, Any]], *, temperature: float = 0.1,
               max_tokens: int | None = None, reasoning: str = "default") -> str:
    body: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature,
                            "provider": provider_routing()}
    if max_tokens:
        body["max_tokens"] = max_tokens
    if option := reasoning_option(reasoning):
        body["reasoning"] = option
    return _content(await _post("/chat/completions", body))


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    return text[start : end + 1] if start != -1 and end > start else text


async def chat_json[T: BaseModel](model: str, messages: list[dict[str, Any]], schema: type[T], *,
                                  temperature: float = 0.1, reasoning: str = "default") -> T:
    """Chat call whose answer must validate against `schema`. One repair attempt on bad JSON."""
    json_schema = strict_schema(schema.model_json_schema())
    schema_text = json.dumps(json_schema, ensure_ascii=False)
    instruction = {
        "role": "system",
        "content": "Reply with a single JSON object only, no prose, matching this JSON Schema:\n" + schema_text,
    }
    body: dict[str, Any] = {
        "model": model,
        "messages": [instruction, *messages],
        "temperature": temperature,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "strict": False, "schema": json_schema},
        },
        "provider": provider_routing(),
    }
    if option := reasoning_option(reasoning):
        body["reasoning"] = option
    text = _content(await _post("/chat/completions", body))
    try:
        return schema.model_validate_json(_extract_json(text))
    except ValidationError as exc:
        log.debug("model returned invalid JSON, retrying once", model=model)
        body["messages"] = [
            *body["messages"],
            {"role": "assistant", "content": text},
            {"role": "user", "content": f"That JSON was invalid ({exc.errors()[:3]}). Reply with corrected JSON only."},
        ]
        body["temperature"] = 0
        text = _content(await _post("/chat/completions", body))
        try:
            return schema.model_validate_json(_extract_json(text))
        except ValidationError as exc2:
            raise LLMError(f"Model {model} did not return valid {schema.__name__} JSON") from exc2


async def speech_to_text(
    model: str, audio_b64: str, audio_format: str, language: str = ""
) -> tuple[str, dict[str, Any]]:
    """OpenRouter's dedicated transcription endpoint (e.g. Whisper). Returns (text, usage)."""
    body: dict[str, Any] = {"model": model, "input_audio": {"data": audio_b64, "format": audio_format}}
    if language:
        body["language"] = language
    data = await _post("/audio/transcriptions", body)
    if "text" not in data:
        raise LLMError(f"Unexpected transcription response: {str(data)[:300]}")
    return str(data["text"] or ""), data.get("usage") or {}


async def embed(model: str, text: str) -> list[float]:
    data = await _post("/embeddings", {"model": model, "input": text})
    try:
        return list(data["data"][0]["embedding"])
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected embeddings response: {str(data)[:300]}") from exc
