import { Link } from "react-router";
import type { ReelCard as Reel } from "../api/types";
import { duration, patternFor, timeAgo } from "../lib/format";
import { VerdictBadge } from "./ui";

export function ReelCard({ reel }: { reel: Reel }) {
  const summary = reel.summary;
  return (
    <article>
      <Link className="card-link" to={`/r/${reel.reel_id}`}>
        <div className="thumb" data-p={patternFor(reel.reel_id)}>
          {reel.stale && <span className="stale-tag">Re-check due</span>}
          <span className="play" aria-hidden="true">▶</span>
          {reel.duration_s ? <span className="dur">{duration(reel.duration_s)}</span> : null}
        </div>
        <div className="card-body">
          <p className="card-meta">
            <span>{reel.creator_handle ? `@${reel.creator_handle}` : "Unknown creator"}</span>
            <span>{reel.topic_tags[0] ?? ""}</span>
          </p>
          <h3 className="card-claim">{summary?.claim_text ?? "No checkable claims found"}</h3>
          <div className="card-foot">
            {summary && <VerdictBadge verdict={summary.verdict} />}
            <span className="card-count">
              {summary ? `${summary.claim_count} ${summary.claim_count === 1 ? "claim" : "claims"}` : ""}
            </span>
          </div>
          <p className="card-time">
            {timeAgo(reel.checked_at)} · {reel.request_count} {reel.request_count === 1 ? "request" : "requests"}
            {!reel.stale && ` · re-check ${timeAgo(reel.expires_at)}`}
          </p>
        </div>
      </Link>
    </article>
  );
}

export function ReelGrid({ reels }: { reels: Reel[] }) {
  return (
    <div className="reel-grid">
      {reels.map((reel) => <ReelCard key={reel.reel_id} reel={reel} />)}
    </div>
  );
}
