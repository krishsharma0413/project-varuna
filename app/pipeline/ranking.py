"""Source credibility ranking, read from the public YAML file on every use (hot-editable)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import yaml

from app.config import get_config, resolve_path
from app.log import log

# Second-level suffixes where the registrable domain has three labels (example.gov.in).
MULTI_PART_SUFFIXES = {
    "gov.in", "nic.in", "co.in", "org.in", "net.in", "ac.in", "edu.in", "res.in", "ernet.in",
    "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "gov.au", "co.jp", "com.br", "co.nz",
}
RANK_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


def hostname(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def registrable_domain(host: str) -> str:
    """example.gov.in -> example.gov.in, news.example.com -> example.com (independence checks)."""
    parts = host.lower().strip(".").split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_PART_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def load_rankings() -> dict[str, Any]:
    path = resolve_path(get_config().verification.source_rankings_file)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        log.exception("could not read source rankings", exc, path=str(path))
        return {"version": None, "ranks": {}, "sources": []}
    data.setdefault("sources", [])
    return data


def lookup(host: str, rankings: dict[str, Any]) -> dict[str, str]:
    """Longest matching domain suffix wins: sci.gov.in beats gov.in."""
    best: dict[str, Any] | None = None
    for entry in rankings.get("sources", []):
        domain = str(entry.get("domain", "")).lower()
        if domain and (host == domain or host.endswith("." + domain)):
            if best is None or len(domain) > len(best["domain"]):
                best = entry
    if best is None:
        return {"rank": get_config().verification.default_rank, "kind": "other"}
    return {"rank": str(best.get("rank", "D")), "kind": str(best.get("kind", "other"))}
