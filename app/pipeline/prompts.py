"""Prompt templates, loaded from prompts.yaml (next to config.yaml, else the repo root).

Read fresh on every use, like config.yaml. An invalid file (YAML error, missing prompt, unknown or
missing placeholder) is ignored in favour of the last valid version. `version()` is the file's
`version` plus a hash of its content, and is stored with every check.
"""

from __future__ import annotations

import hashlib
import string
import threading
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.config import config_path
from app.log import log

REPO_FILE = Path(__file__).resolve().parents[2] / "prompts.yaml"

# prompt name -> (allowed placeholders, required placeholders)
FIELDS: dict[str, tuple[set[str], set[str]]] = {
    "topic_gate": ({"topics", "caption"}, {"topics", "caption"}),
    "transcribe": (set(), set()),
    "ocr": (set(), set()),
    "cleanup": ({"caption", "transcript", "ocr"}, {"caption", "transcript", "ocr"}),
    "claims": ({"today", "max_claims", "topics", "text"}, {"today", "max_claims", "topics", "text"}),
    "verdict": ({"today", "claim", "claim_type", "delivery", "context", "evidence", "research", "min_sources"},
                {"claim", "evidence", "research"}),
    "research_more": ({"round", "max_rounds", "queries_per_round", "searched"}, set()),
    "research_last": ({"round", "max_rounds", "searched"}, set()),
}


class PromptsError(Exception):
    pass


@dataclass(frozen=True)
class Prompts:
    version: str
    texts: dict[str, str]

    def render(self, name: str, **values: object) -> str:
        return self.texts[name].format(**values)


_lock = threading.Lock()
_last_good: Prompts | None = None
_last_error: str | None = None


def prompts_path() -> Path:
    try:
        beside_config = config_path().parent / "prompts.yaml"
        if beside_config.is_file():
            return beside_config
    except FileNotFoundError:
        pass
    return REPO_FILE


def placeholders(template: str) -> set[str]:
    try:
        return {field for _, field, _, _ in string.Formatter().parse(template) if field is not None}
    except ValueError as exc:  # a lone { or }
        raise PromptsError(f"bad braces ({exc}); write literal braces as {{{{ or }}}}") from None


def parse(content: str) -> Prompts:
    try:
        raw = yaml.safe_load(content) or {}
    except yaml.YAMLError as exc:
        raise PromptsError(f"YAML error: {exc}") from None
    if not isinstance(raw, dict):
        raise PromptsError("the file must be a mapping of prompt names to text")
    unknown = set(raw) - set(FIELDS) - {"version"}
    if unknown:
        raise PromptsError(f"unknown keys: {', '.join(sorted(unknown))}")
    texts: dict[str, str] = {}
    for name, (allowed, required) in FIELDS.items():
        text = raw.get(name)
        if not isinstance(text, str) or (not text.strip() and name not in ("research_more", "research_last")):
            raise PromptsError(f"{name}: missing or not text")
        used = placeholders(text)
        if used - allowed:
            raise PromptsError(f"{name}: unknown placeholders {', '.join(sorted(used - allowed))}")
        if required - used:
            raise PromptsError(f"{name}: missing placeholders {', '.join(sorted(required - used))}")
        texts[name] = text.strip()
    digest = hashlib.sha256(content.encode()).hexdigest()[:8]
    return Prompts(version=f"{str(raw.get('version') or 'v?').strip()}+{digest}", texts=texts)


def get() -> Prompts:
    global _last_good, _last_error
    path = prompts_path()
    try:
        prompts = parse(path.read_text(encoding="utf-8"))
    except (OSError, PromptsError) as exc:
        with _lock:
            if _last_good is None:
                raise PromptsError(f"{path.name} is invalid: {exc}") from None
            message = f"{path.name} is invalid, using the last valid version: {exc}"
            if message != _last_error:
                _last_error = message
                log.error(message)
            return _last_good
    with _lock:
        _last_good = prompts
        _last_error = None
    return prompts


def render(name: str, **values: object) -> str:
    return get().render(name, **values)


def version() -> str:
    return get().version
