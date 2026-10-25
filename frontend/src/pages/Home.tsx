import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { useHero, useReels, useTopics } from "../api/hooks";
import type { Hero, ReelCard as Reel } from "../api/types";
import { ReelGrid } from "../components/ReelCard";
import {
  EmptyNotice, ErrorNotice, SearchIcon, SectionHead, SkeletonGrid, VerdictBadge, VerdictLegend,
} from "../components/ui";
import { minutesAgo } from "../lib/format";
import { VERDICTS } from "../lib/verdicts";

export function Home() {
  const [params] = useSearchParams();
  const reels = useReels({ topic: params.get("topic") ?? undefined, q: params.get("q") ?? undefined });
  const firstPage = reels.data?.pages[0]?.items ?? [];

  return (
    <>
      <Ticker reels={firstPage} />
      <HeroSection />
      <LatestSection />
      <section className="sec">
        <div className="wrap">
          <SectionHead
            num="02"
            title={<>How it <em>works</em></>}
            sub="varuna fact checker reads the whole reel, splits it into claims, and checks each one in three tiers of sources."
          />
          <ol className="steps">
            <li><span className="step-n">1</span><h3>Read the reel</h3><p>Speech is transcribed, on-screen text is read from frames, and the caption is added.</p></li>
            <li><span className="step-n">2</span><h3>Split into claims</h3><p>Each checkable statement is separated. Opinions and predictions are marked, not judged.</p></li>
            <li><span className="step-n">3</span><h3>Check in three tiers</h3><p>Official records first, then existing fact-checks, then ranked news and web sources.</p></li>
            <li><span className="step-n">4</span><h3>Publish with an expiry</h3><p>Every result shows its sources and has a re-check date, because facts change.</p></li>
          </ol>
        </div>
      </section>
      <section className="sec">
        <div className="wrap">
          <SectionHead num="03" title={<>What each <em>verdict</em> means</>} sub="Six verdicts, each with its own mark, so none of them depend on colour." />
          <VerdictLegend />
        </div>
      </section>
      <section className="sec invert">
        <div className="wrap">
          <SectionHead num="04" title={<>Check <em>a reel</em></>} sub="Invited members can submit any Instagram reel link. If someone already asked about it, you get the same result." />
          <Link className="btn btn-primary" to="/check">Check a reel</Link>
        </div>
      </section>
    </>
  );
}

function Ticker({ reels }: { reels: Reel[] }) {
  const items = reels.filter((r) => r.summary).slice(0, 10);
  if (items.length < 3) return null;
  const row = items.map((r) => (
    <span className="ticker-item" key={r.reel_id}>
      <b>{VERDICTS[r.summary!.verdict].glyph} {VERDICTS[r.summary!.verdict].label}</b>
      {r.summary!.claim_text}
    </span>
  ));
  return (
    <div className="ticker" aria-hidden="true">
      <div className="ticker-track">{row}{row}</div>
    </div>
  );
}

function HeroSection() {
  const { data, isPending, error, refetch } = useHero();
  return (
    <section className="hero invert" aria-label="Most checked claim">
      <div className="wrap hero-inner">
        {isPending ? (
          <div className="skeleton" style={{ height: 360, gridColumn: "1 / -1" }} aria-busy="true" />
        ) : error ? (
          <div style={{ gridColumn: "1 / -1" }}><ErrorNotice error={error} retry={() => void refetch()} /></div>
        ) : data ? (
          <HeroContent hero={data} />
        ) : (
          <div style={{ gridColumn: "1 / -1" }}>
            <p className="eyebrow"><span className="live" aria-hidden="true" />Nothing checked yet</p>
            <h1 className="hero-claim">Question <em>before</em> you believe.</h1>
            <div className="hero-actions">
              <Link className="btn btn-primary" to="/check">Check the first reel</Link>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function HeroContent({ hero }: { hero: Hero }) {
  const last = minutesAgo(hero.last_checked_at);
  return (
    <>
      <div>
        <p className="eyebrow">
          <span className="live" aria-hidden="true" />
          {hero.fallback ? "Latest check" : `Most checked right now · last ${hero.window_hours} hours`}
        </p>
        <h1 className="hero-claim">“{hero.claim.text}”</h1>
        <div className="hero-verdict-row">
          <VerdictBadge verdict={hero.claim.verdict} large />
          <p className="hero-summary">{hero.claim.explanation}</p>
        </div>
        <div className="hero-actions">
          <Link className="btn btn-primary" to={`/r/${hero.reel_id}`}>Read the full check</Link>
          <a className="btn btn-ghost" href="#latest">See latest checks</a>
        </div>
      </div>
      <aside aria-label="How often this claim was checked">
        <dl className="stats">
          <div className="stat"><dt>Checks requested</dt><dd>{hero.checks}</dd></div>
          <div className="stat"><dt>Unique people</dt><dd>{hero.unique_people ?? "—"}</dd></div>
          <div className="stat"><dt>Distinct reels</dt><dd>{hero.distinct_reels}</dd></div>
          <div className="stat"><dt>Last checked</dt><dd>{last.value}<small>{last.unit}</small></dd></div>
        </dl>
        {hero.claim.sources.length > 0 && (
          <div className="hero-sources">
            <span className="mini-label">Sources</span>
            <ol>
              {hero.claim.sources.slice(0, 3).map((s) => (
                <li key={s.url}>
                  <span className="tier">T{s.tier}</span>
                  <a href={s.url} target="_blank" rel="noopener noreferrer nofollow">{s.title || s.domain}</a>
                </li>
              ))}
            </ol>
          </div>
        )}
      </aside>
    </>
  );
}

function LatestSection() {
  const [params, setParams] = useSearchParams();
  const topic = params.get("topic") ?? "";
  const q = params.get("q") ?? "";
  const [draft, setDraft] = useState(q);
  const topics = useTopics();
  const reels = useReels({ topic: topic || undefined, q: q || undefined });

  useEffect(() => {
    const id = window.setTimeout(() => {
      if (draft.trim() === q) return;
      const next = new URLSearchParams(params);
      if (draft.trim()) next.set("q", draft.trim());
      else next.delete("q");
      setParams(next, { replace: true, preventScrollReset: true });
    }, 350);
    return () => window.clearTimeout(id);
  }, [draft, q, params, setParams]);

  const chooseTopic = (value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set("topic", value);
    else next.delete("topic");
    setParams(next, { preventScrollReset: true });
  };

  const items = reels.data?.pages.flatMap((p) => p.items) ?? [];
  return (
    <section className="sec" id="latest">
      <div className="wrap">
        <SectionHead num="01" title={<>Latest <em>checks</em></>} sub="Reels people asked about, newest first. Every verdict links to the sources behind it." />
        <div className="toolbar">
          <div className="chips" role="group" aria-label="Filter by topic">
            <button type="button" className="chip" aria-pressed={!topic} onClick={() => chooseTopic("")}>All</button>
            {topics.data?.items.slice(0, 10).map((t) => (
              <button type="button" key={t.topic} className="chip" aria-pressed={topic === t.topic} onClick={() => chooseTopic(t.topic)}>
                {t.topic}
              </button>
            ))}
          </div>
          <label className="search">
            <span className="sr-only">Search by reel link, @handle or claim</span>
            <SearchIcon />
            <input type="search" placeholder="Reel link, @handle or claim" value={draft} onChange={(e) => setDraft(e.target.value)} />
          </label>
        </div>
        {reels.isPending ? (
          <SkeletonGrid />
        ) : reels.error ? (
          <ErrorNotice error={reels.error} retry={() => void reels.refetch()} />
        ) : items.length === 0 ? (
          topic || q ? (
            <EmptyNotice title="Nothing matches" cta={false}>Try another topic or search term.</EmptyNotice>
          ) : (
            <EmptyNotice title="No checks yet">Once a reel is checked, it shows up here.</EmptyNotice>
          )
        ) : (
          <>
            <ReelGrid reels={items} />
            {reels.hasNextPage && (
              <div className="load-more">
                <button className="btn btn-ghost" disabled={reels.isFetchingNextPage} onClick={() => void reels.fetchNextPage()}>
                  {reels.isFetchingNextPage ? "Loading…" : "Load more"}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
