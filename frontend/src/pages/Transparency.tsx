import type { ReactNode } from "react";
import { Link } from "react-router";
import { useTransparency } from "../api/hooks";
import type { Transparency as Data } from "../api/types";
import { ErrorNotice, SectionHead } from "../components/ui";

const ROLE_LABEL: Record<string, string> = {
  gate: "Language · topic check",
  transcription: "Speech",
  vision: "Vision",
  small: "Language · light",
  strong: "Language · verdicts",
  embedding: "Matching",
};

const TOOL_LABEL: Record<string, string> = { instaloader: "Instaloader", "yt-dlp": "yt-dlp" };

function hours(h: number): string {
  if (h < 48) return `${h} hours`;
  return `${Math.round(h / 24)} days`;
}

const PROVIDER_NAMES: Record<string, string> = {
  searxng: "SearXNG", selenium: "Browser", serper: "Serper", tavily: "Tavily", brave: "Brave Search API",
};
const ENGINE_NAMES: Record<string, string> = { google: "Google", duckduckgo: "DuckDuckGo", bing: "Bing", brave: "Brave" };

function searchLabel(name: string): string {
  const [provider, engine] = name.split(":");
  const p = PROVIDER_NAMES[provider] ?? provider;
  return engine ? `${p} · ${ENGINE_NAMES[engine] ?? engine}` : p;
}

function list(items: string[]): string {
  return items.length ? items.join(", ") : "none configured";
}

export function Transparency() {
  const { data, isPending, error, refetch } = useTransparency();
  return (
    <>
      <title>Transparency · varuna fact checker</title>
      <section className="hero invert">
        <div className="wrap hero-inner" style={{ gridTemplateColumns: "1fr" }}>
          <div>
            <p className="eyebrow"><span className="live" aria-hidden="true" />Read live from our configuration</p>
            <h1 className="hero-claim">Nothing <em>hidden</em>.</h1>
            <p className="hero-summary" style={{ marginTop: 28 }}>
              Every model, setting and instruction behind each verdict. This page is generated from the same
              configuration the system runs on, so when a model or setting changes, this page changes with it.
            </p>
            {data && (
              <p className="mini-label" style={{ marginTop: 20 }}>
                Pipeline v{data.pipeline_version} · prompts {data.prompt_version} · models via {data.provider}
              </p>
            )}
          </div>
        </div>
      </section>
      {isPending ? (
        <section className="sec"><div className="wrap"><div className="skeleton" style={{ height: 480 }} aria-busy="true" /></div></section>
      ) : error ? (
        <section className="sec"><div className="wrap"><ErrorNotice error={error} retry={() => void refetch()} /></div></section>
      ) : (
        <Body data={data} />
      )}
    </>
  );
}

function Body({ data }: { data: Data }) {
  const x = data.extraction;
  const v = data.verification;
  const model = (role: string) => data.models.find((m) => m.role === role);
  const slug = (role: string) => {
    const m = model(role);
    return m?.slug ? <a className="underline" href={m.url} target="_blank" rel="noopener noreferrer">{m.slug}</a> : <em>not used</em>;
  };

  return (
    <>
      <section className="sec">
        <div className="wrap">
          <SectionHead
            num="01"
            title={<>The <em>models</em></>}
            sub="We run low-cost models while varuna is funded by donations, and will move to stronger ones as funding allows. Every result records the exact models that produced it."
          />
          <div className="model-grid">
            {data.models.filter((m) => m.slug).map((m) => (
              <article key={m.role} className="model-card">
                <span className="mini-label">{ROLE_LABEL[m.role] ?? m.role}</span>
                <h3>{m.step}</h3>
                <a className="model-slug" href={m.url} target="_blank" rel="noopener noreferrer">{m.slug}</a>
                <dl className="kv">
                  <div><dt>Receives</dt><dd>{m.receives}</dd></div>
                  <div><dt>Returns</dt><dd>{m.returns}</dd></div>
                  {m.reasoning && <div><dt>Reasoning</dt><dd>{m.reasoning}</dd></div>}
                </dl>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sec">
        <div className="wrap">
          <SectionHead
            num="02"
            title={<>The <em>flow</em></>}
            sub="What happens between a reel link being submitted and a verdict being published, with the settings in use right now."
          />
          <ol className="flow">
            <Step title="A reel is submitted">
              An invited member pastes an Instagram reel link. If the reel already has a result that hasn't reached
              its re-check date, they get that result and nothing runs again. If a check is already running, they
              join it. New checks are limited to {data.limits.daily_check_cap} a day across everyone.
            </Step>
            <Step title="We read the reel's details">
              The caption, creator handle and length are read with {data.download.tools.map((t) => TOOL_LABEL[t] ?? t).join(", then ")},
              without downloading the video yet. Reels longer than {Math.round(data.download.max_video_seconds / 60)} minutes
              are not checked.
            </Step>
            {data.topic_gate.enabled && (
              <Step title="The topic is checked first">
                {slug("gate")} reads only the caption and decides whether the reel is about one of the topics we cover:
                <span className="chain">
                  {data.topic_gate.topics.map((t) => <code key={t}>{t}</code>)}
                </span>
                Off-topic reels stop here: nothing is downloaded, transcribed or searched, and they don't count
                against the daily limit.{" "}
                {data.topic_gate.empty_caption === "reject"
                  ? "Reels without a caption are turned away, since there's nothing to judge the topic by. "
                  : "Reels without a caption are checked anyway. "}
                A rejection is remembered for {hours(data.topic_gate.remember_hours)}, unless the topic list changes.
              </Step>
            )}
            <Step title="The video is downloaded and taken apart">
              The video is downloaded (up to {data.download.max_video_mb} MB). Frames are captured at intervals
              that depend on length:{" "}
              {x.frame_intervals.map((r, i) => (
                <span key={i}>
                  {i === x.frame_intervals.length - 1 && i > 0 ? "longer" : `up to ${r.up_to_seconds}s`}, every {r.every_seconds}s{i < x.frame_intervals.length - 1 ? "; " : ". "}
                </span>
              ))}
              Near-duplicate frames are dropped and at most {x.max_frames} are kept. The audio is cut into
              {" "}{x.chunk_seconds}-second chunks.
            </Step>
            <Step title="Speech becomes text">
              Each audio chunk goes to {slug("transcription")}{" "}
              ({x.transcription_api === "stt" ? "a dedicated speech-to-text model" : "an audio-capable language model"}),
              with language set to {x.transcription_language}. The transcript stays in the language spoken.
            </Step>
            <Step title="On-screen text is read">
              {x.ocr_engine === "vision" ? (
                <>Up to {x.ocr_frames} evenly spaced frames go to {slug("vision")}, which writes out captions, overlays and documents shown in the video.</>
              ) : (
                <>Reading on-screen text is currently switched off.</>
              )}
            </Step>
            <Step title="Everything is merged and split into claims">
              {slug("small")} merges the caption, transcript and on-screen text into one clean text, without adding
              anything, then splits it into at most {x.max_claims_per_reel} separate claims. Each is classified as a
              verifiable fact, a contested claim, an opinion or a prediction. Opinions are never judged, and
              predictions wait until they fall due.
            </Step>
            <Step title="Evidence is gathered in three tiers">
              <ul className="flow-list">
                <li><strong>Tier 1, official records:</strong> searches limited to {list(v.official_sites)}.</li>
                <li>
                  <strong>Tier 2, existing fact-checks:</strong>{" "}
                  {v.factcheck_api_enabled ? "the Google Fact Check Tools database, plus " : ""}searches limited to {list(v.factcheck_sites)}.
                </li>
                <li>
                  <strong>Tier 3, the open web:</strong> up to {v.max_queries_per_claim} searches per claim,{" "}
                  {v.results_per_query} results each.
                </li>
              </ul>
              {v.search_chain.length > 0 ? (
                <>
                  Searches go through a fallback chain. The first option that answers is used; if one is blocked or
                  fails, it's paused for a while and the next is tried:
                  <span className="chain">
                    {v.search_chain.map((name, i) => (
                      <span key={name} className="chain-step">
                        {i > 0 && <span className="chain-arrow" aria-hidden="true">→</span>}
                        <code>{searchLabel(name)}</code>
                      </span>
                    ))}
                  </span>
                </>
              ) : (
                <>Web search is not configured yet. </>
              )}
              Every source gets a credibility rank from our <Link className="underline" to="/method#sources">public ranking</Link>;
              unlisted sources get rank {v.default_rank}. The best {v.max_evidence} pieces of evidence are kept.
            </Step>
            <Step title="A verdict is decided, then checked by rules">
              {slug("strong")} reads the claim and the ranked evidence and proposes a verdict, an explanation and the
              sources it relies on, leaving out sources about a different place, time or event.{" "}
              {v.research_rounds > 1 && (
                <>
                  If the evidence doesn't settle the claim, it can ask for up to {v.follow_up_queries_per_round} new
                  searches built from what it has learned so far (names, dates, documents), and decides again with up
                  to {v.new_evidence_per_round} new sources added. That's at most {v.research_rounds} search rounds per claim.{" "}
                </>
              )}
              Fixed rules then override it where needed: True or False needs at least{" "}
              {v.min_independent_sources} independent sources, contested claims never get True or False, and anything
              the evidence can't settle becomes Unverified.
            </Step>
            <Step title="The result is published with a re-check date">
              Results expire after {hours(data.ttl_hours.breaking)} for breaking news, {hours(data.ttl_hours.ongoing)} for
              ongoing stories and {hours(data.ttl_hours.settled)} for settled events. After that, the next request checks
              the reel again and the old result moves into its public history.
            </Step>
          </ol>
        </div>
      </section>

      <section className="sec">
        <div className="wrap">
          <SectionHead num="03" title={<>What we <em>keep</em></>} sub="Only what a result needs, for as long as it needs it." />
          <ul className="legend">
            <li><div><span className="verdict">Deleted</span></div><p>The video, its frames and its audio, as soon as a check finishes.</p></li>
            <li><div><span className="verdict">Public</span></div><p>Claims, verdicts, explanations, sources and the cleaned text we read from the reel, for every check.</p></li>
            <li>
              <div><span className="verdict">History</span></div>
              <p>
                Past results stay visible when a reel is re-checked
                {data.retention.history_max_entries ? ` (the last ${data.retention.history_max_entries})` : ""}.
                {data.retention.history_keeps_raw_text ? " Raw transcripts are kept with them." : " Raw transcripts are dropped from older results."}
              </p>
            </li>
            <li><div><span className="verdict">Hashed</span></div><p>Who asked for a check is stored only as a one-way hash, to count unique people, and deleted after {data.retention.requests_days} days.</p></li>
            <li><div><span className="verdict">Logs</span></div><p>Technical logs record a request ID, time, level and message so problems can be traced. Job records are deleted after {data.retention.jobs_days} days.</p></li>
            <li><div><span className="verdict">Creators</span></div><p>A creator's record is shown only after {data.creators_min_sample} checked claims, as counts of claims rather than judgments of people.</p></li>
          </ul>
          <p className="note">Submissions are limited to {data.limits.submit.join(" and ")} per account so no single person can steer what gets checked.</p>
        </div>
      </section>

      <section className="sec">
        <div className="wrap">
          <SectionHead
            num="04"
            title={<>The exact <em>instructions</em></>}
            sub={`The prompts given to the models, word for word (version ${data.prompt_version}). Text in {braces} is filled in for each reel.`}
          />
          {data.prompts.map((p) => (
            <details key={p.name} className="details">
              <summary>{p.name}</summary>
              <pre className="prompt">{p.text}</pre>
            </details>
          ))}
          <p className="note">
            See also <Link to="/method">how we check</Link> and the <Link to="/method#sources">source rankings</Link>.
          </p>
        </div>
      </section>
    </>
  );
}

function Step({ title, children }: { title: string; children: ReactNode }) {
  return (
    <li>
      <span className="flow-n" aria-hidden="true" />
      <div>
        <h3>{title}</h3>
        <div className="flow-body">{children}</div>
      </div>
    </li>
  );
}
