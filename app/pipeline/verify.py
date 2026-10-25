"""Three-tier verification of one claim, then rule checks on the model's verdict."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.config import Config
from app.log import log
from app.models import ClaimResult, Source, Verdict
from app.pipeline import llm, prompts
from app.pipeline.claims import ExtractedClaim, claim_id, normalize
from app.pipeline.ranking import RANK_ORDER, hostname, load_rankings, lookup, registrable_domain
from app.pipeline.search import Hit, factcheck_search, web_search
from app.services.reels import fresh_claim

Stance = Literal["supports", "contradicts", "related"]


class SourceStance(BaseModel):
    id: int
    stance: Stance


class VerdictOut(BaseModel):
    # Field order is the order the model writes them in: pin down the assertion and how each source
    # relates to it before committing to a verdict, then say what to search next.
    assertion: str = Field(description="Exactly what the claim asserts, in one sentence.")
    # No defaults: required fields make the model write them out (an empty list is a valid answer).
    sources: list[SourceStance] = Field(description="Every evidence item about the same matter, with its stance.")
    verdict: Literal["true", "false", "misleading", "unverified", "outdated", "opinion"]
    explanation: str
    follow_up_queries: list[str] = Field(description="New web searches for the next round; [] when done.")


async def _safe(label: str, coro: Any) -> list[Hit]:
    try:
        return await coro
    except Exception as exc:
        log.exception("evidence source failed", exc, source=label)
        return []


def _to_sources(batches: list[tuple[str, list[Hit]]]) -> list[Source]:
    """Rank and dedupe hits (by URL, keeping the best tier), best first."""
    default_tier = {"official": 1, "factcheck_api": 2, "factcheck_sites": 2}
    rankings = load_rankings()
    by_url: dict[str, Source] = {}
    for label, hits in batches:
        for hit in hits:
            host = hostname(hit.url)
            if not host:
                continue
            ranked = lookup(host, rankings)
            tier = default_tier.get(label, 3)
            if ranked["kind"] == "primary":
                tier = 1
            elif ranked["kind"] == "factcheck":
                tier = min(tier, 2)
            source = Source(
                url=hit.url, domain=host, title=hit.title[:300], snippet=hit.snippet[:600],
                tier=tier, kind=ranked["kind"], rank=ranked["rank"], published=hit.published[:40],
                found_via=f"{label} via {hit.served_by}" if hit.served_by else label,
            )
            current = by_url.get(hit.url)
            if current is None or source.tier < current.tier:
                by_url[hit.url] = source
    return sorted(by_url.values(), key=lambda s: (s.tier, RANK_ORDER.get(s.rank, 9)))


async def gather_evidence(claim: ExtractedClaim, config: Config) -> list[Source]:
    """Round 1: official sites, fact-checks and the open web, from the claim's own search queries."""
    queries = (claim.search_queries or [claim.text])[: config.search.max_queries_per_claim]
    base = queries[0]
    verification = config.verification
    labels = ["official", "factcheck_api", "factcheck_sites", *["web"] * len(queries)]
    batches = await asyncio.gather(
        _safe("official", web_search(base, verification.official_sites)),
        _safe("factcheck_api", factcheck_search(claim.text)),
        _safe("factcheck_sites", web_search(base, verification.factcheck_sites)),
        *(_safe("web", web_search(q)) for q in queries),
    )
    return _to_sources(list(zip(labels, batches, strict=True)))[: verification.max_evidence]


async def follow_up_evidence(queries: list[str], known: list[Source], round_no: int, config: Config) -> list[Source]:
    """A follow-up round: the model's new queries on the open web. Only sources not already known."""
    label = f"follow-up {round_no}"
    batches = await asyncio.gather(*(_safe(label, web_search(q)) for q in queries))
    seen = {s.url for s in known}
    fresh = [s for s in _to_sources([(label, hits) for hits in batches]) if s.url not in seen]
    return fresh[: config.verification.research.new_evidence_per_round]


def new_queries(proposed: list[str], searched: list[str], limit: int) -> list[str]:
    """The model's follow-up queries minus blanks and repeats (case- and punctuation-insensitive)."""
    done = {normalize(q) for q in searched}
    picked: list[str] = []
    for query in proposed:
        key = normalize(query)
        if key and key not in done:
            done.add(key)
            picked.append(query.strip()[:200])
    return picked[:limit]


def enforce_rules(
    verdict: Verdict, explanation: str, stances: list[tuple[Source, str]], claim_type: str, min_independent: int
) -> tuple[Verdict, str]:
    """Rules the model must not override: contested claims get no true/false; "true" needs
    `min_independent` organisations whose sources *support* the assertion, "false" needs that many that
    *contradict* it. Sources that are only related (background, a related rule) never count."""
    if claim_type == "contested" and verdict in ("true", "false"):
        return "unverified", explanation + " This is a contested claim, so we show the sources rather than rule on it."
    needed = {"true": "supports", "false": "contradicts"}.get(verdict)
    if needed:
        organisations = {registrable_domain(s.domain) for s, stance in stances if stance == needed}
        if len(organisations) < min_independent:
            word = "confirm" if verdict == "true" else "contradict"
            return "unverified", (
                explanation + f" Fewer than {min_independent} independent sources directly {word} it, "
                "so we can't rule yet."
            )
    return verdict, explanation


def expiry(claim: ExtractedClaim, now: datetime, config: Config) -> datetime:
    if claim.type == "prediction" and claim.resolution_date:
        try:
            due = datetime.combine(date.fromisoformat(claim.resolution_date), datetime.min.time(), UTC)
            if due > now:
                return due
        except ValueError:
            pass
    hours = {
        "breaking": config.ttl.breaking_hours,
        "ongoing": config.ttl.ongoing_hours,
        "settled": config.ttl.settled_hours,
    }.get(claim.volatility, config.ttl.default_hours)
    return now + timedelta(hours=hours)


def _format_evidence(sources: list[Source]) -> str:
    if not sources:
        return "(no evidence found)"
    return "\n".join(
        f"[{i}] {s.published or 'date unknown'} | tier {s.tier}, {s.kind}, rank {s.rank}, {s.domain} | "
        f"{s.title} | {s.snippet}"
        for i, s in enumerate(sources)
    )


async def decide(claim: ExtractedClaim, context: str, config: Config, now: datetime
                 ) -> tuple[VerdictOut, list[Source], list[str], int]:
    """Search, ask for a verdict, and repeat with the model's follow-up queries until it's satisfied,
    nothing new turns up, or `verification.research.max_rounds` is reached."""
    research = config.verification.research
    evidence = await gather_evidence(claim, config)
    searched = list((claim.search_queries or [claim.text])[: config.search.max_queries_per_claim])
    round_no = 1
    while True:
        last = round_no >= research.max_rounds
        note = prompts.render(
            "research_last" if last else "research_more", round=round_no, max_rounds=research.max_rounds,
            queries_per_round=research.queries_per_round, searched="; ".join(searched) or "(none)",
        )
        prompt = prompts.render(
            "verdict", today=now.date().isoformat(), claim=claim.text, claim_type=claim.type,
            delivery=claim.delivery, context=context[:1500] or "(none)", evidence=_format_evidence(evidence),
            research=note, min_sources=config.verification.min_independent_sources,
        )
        decision = await llm.chat_json(config.openrouter.models.strong, [{"role": "user", "content": prompt}],
                                        VerdictOut, reasoning=config.openrouter.reasoning.verdict)
        log.info("verdict decided", claim_id=claim_id(claim.text), round=round_no, verdict=decision.verdict,
                 assertion=decision.assertion[:300],
                 stances=",".join(f"{item.id}:{item.stance}" for item in decision.sources),
                 follow_ups=" | ".join(decision.follow_up_queries)[:500])
        follow = [] if last else new_queries(decision.follow_up_queries, searched, research.queries_per_round)
        if not follow:
            return decision, evidence, searched, round_no
        round_no += 1
        fresh = await follow_up_evidence(follow, evidence, round_no, config)
        searched.extend(follow)
        log.info("follow-up search", round=round_no, queries=" | ".join(follow), new_sources=len(fresh))
        if not fresh:  # nothing new to read, so asking again would give the same answer
            return decision, evidence, searched, round_no
        evidence = evidence + fresh  # appended, so the ids the model already saw stay valid


async def verify_claim(claim: ExtractedClaim, context: str, config: Config) -> ClaimResult:
    now = datetime.now(UTC)
    cid = claim_id(claim.text)
    base = {
        "claim_id": cid, "text": claim.text, "original": claim.original, "delivery": claim.delivery,
        "type": claim.type, "volatility": claim.volatility, "topic_tags": claim.topic_tags,
        "resolution_date": claim.resolution_date,
    }

    reusable = await fresh_claim(cid)
    if reusable:
        log.info("reusing a fresh verdict for a repeated claim", claim_id=cid)
        return ClaimResult(**{**reusable, **base, "reused": True})

    prediction_pending = claim.type == "prediction" and expiry(claim, now, config) > now + timedelta(
        hours=config.ttl.default_hours
    )
    if claim.type == "opinion" or prediction_pending:
        explanation = (
            "This is an opinion or value judgement, so it can't be checked as true or false."
            if claim.type == "opinion"
            else f"This is a prediction. It will be checked again on {claim.resolution_date}."
        )
        return ClaimResult(**base, verdict="opinion", explanation=explanation, sources=[],
                           checked_at=now, expires_at=expiry(claim, now, config))

    decision, evidence, searched, rounds = await decide(claim, context, config, now)
    stances: list[tuple[Source, str]] = []
    seen: set[int] = set()
    for item in decision.sources:
        if 0 <= item.id < len(evidence) and item.id not in seen:
            seen.add(item.id)
            stances.append((evidence[item.id], item.stance))
    verdict, explanation = enforce_rules(
        decision.verdict, decision.explanation.strip(), stances, claim.type,
        config.verification.min_independent_sources,
    )
    if verdict != decision.verdict:
        log.info("verdict changed by rules", claim_id=cid, model=decision.verdict, final=verdict)
    # Direct evidence first, then related background; each source keeps its stance for the result page.
    stances.sort(key=lambda pair: pair[1] == "related")
    cited = [source.model_copy(update={"stance": stance}) for source, stance in stances]
    if verdict == "unverified" and not cited:
        cited = evidence[:3]
    return ClaimResult(**base, verdict=verdict, explanation=explanation, sources=cited, queries=searched,
                       search_rounds=rounds, checked_at=now, expires_at=expiry(claim, now, config))
