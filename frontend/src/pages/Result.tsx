import { useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError, api } from "../api/client";
import { useReel } from "../api/hooks";
import type { CheckResult, ReelDetail, Verdict } from "../api/types";
import { ClaimTable } from "../components/ClaimTable";
import { EmptyNotice, ErrorNotice, VerdictBadge } from "../components/ui";
import { duration, formatDate } from "../lib/format";

export function Result() {
  const { reelId = "" } = useParams();
  const { data, isPending, error, refetch } = useReel(reelId);

  if (isPending) {
    return <section className="sec"><div className="wrap"><div className="skeleton" style={{ height: 420 }} aria-busy="true" /></div></section>;
  }
  if (error) {
    return (
      <section className="sec">
        <div className="wrap">
          {error instanceof ApiError && error.status === 404 ? (
            <EmptyNotice title="Not checked yet">Nobody has asked about this reel yet. Submit it to start a check.</EmptyNotice>
          ) : (
            <ErrorNotice error={error} retry={() => void refetch()} />
          )}
        </div>
      </section>
    );
  }
  return <ResultView reel={data} />;
}

function ResultView({ reel }: { reel: ReelDetail }) {
  const current = reel.current;
  const summary = current.summary;
  return (
    <>
      <title>{`${summary?.claim_text ?? "Reel check"} · varuna fact checker`}</title>
      <section className="hero invert">
        <div className="wrap hero-inner result-head">
          <div>
            <p className="eyebrow">
              {reel.creator_handle ? <Link to={`/c/${reel.creator_handle}`}>@{reel.creator_handle}</Link> : "Unknown creator"}
              {" · "}
              {summary ? `${summary.claim_count} ${summary.claim_count === 1 ? "claim" : "claims"} checked` : "No claims"}
            </p>
            <h1 className="hero-claim" style={{ fontSize: "clamp(2.4rem, 6vw, 6rem)" }}>
              {summary ? `“${summary.claim_text}”` : "No checkable claims found"}
            </h1>
          </div>
          {summary && <div><VerdictBadge verdict={summary.verdict} large /></div>}
        </div>
      </section>

      <section className="sec">
        <div className="wrap">
          {reel.stale && (
            <p className="stale-banner">This result is past its re-check date. The next request for this reel will check it again; the current result then moves into the history below.</p>
          )}
          <div className="result-box">
            <div className="result-meta">
              <div>
                <span className="mini-label">Reel</span>
                <span><a className="underline" href={reel.permalink} target="_blank" rel="noopener noreferrer nofollow">Open on Instagram</a>{reel.duration_s ? ` · ${duration(reel.duration_s)}` : ""}</span>
              </div>
              <div><span className="mini-label">Read from</span><span>{current.inputs_used.join(", ")}</span></div>
              <div><span className="mini-label">Checked</span><span>{formatDate(current.checked_at)}</span></div>
              <div><span className="mini-label">Re-check after</span><span>{formatDate(current.expires_at)}</span></div>
            </div>
            <ClaimTable claims={current.claims} />
          </div>

          {current.extraction.cleaned_text && (
            <details className="details">
              <summary>What we read from the reel</summary>
              <pre>{current.extraction.cleaned_text}</pre>
            </details>
          )}

          {reel.history.length > 0 && (
            <details className="details" open>
              <summary>Earlier results ({reel.history.length})</summary>
              {reel.history.map((entry) => <HistoryEntry key={entry.checked_at} entry={entry} />)}
            </details>
          )}

          <details className="details">
            <summary>Dispute a verdict</summary>
            <DisputeForm reelId={reel.reel_id} />
          </details>
        </div>
      </section>
    </>
  );
}

function HistoryEntry({ entry }: { entry: CheckResult }) {
  const counts = Object.entries(entry.summary?.counts ?? {}).filter(([, n]) => n > 0) as [Verdict, number][];
  return (
    <details className="history-item">
      <summary>
        <span>{formatDate(entry.checked_at)}</span>
        <span className="counts">
          {counts.map(([verdict, n]) => (
            <span key={verdict}><VerdictBadge verdict={verdict} /> ×{n}</span>
          ))}
        </span>
      </summary>
      <div className="result-box"><ClaimTable claims={entry.claims} /></div>
    </details>
  );
}

function DisputeForm({ reelId }: { reelId: string }) {
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState("");
  const [state, setState] = useState<{ status: "idle" | "sending" | "sent" } | { status: "error"; message: string }>({ status: "idle" });

  if (state.status === "sent") {
    return <p className="form-ok" style={{ marginBottom: 24 }}>Thanks. Your dispute was received and will be reviewed. Verdicts change only with new evidence, and every change is logged.</p>;
  }
  return (
    <form
      className="form"
      style={{ paddingBottom: 28 }}
      onSubmit={async (e) => {
        e.preventDefault();
        setState({ status: "sending" });
        try {
          await api("/disputes", { method: "POST", body: JSON.stringify({ reel_id: reelId, message, contact: contact || null }) });
          setState({ status: "sent" });
        } catch (err) {
          setState({ status: "error", message: err instanceof ApiError ? err.message : "Couldn't send. Please try again." });
        }
      }}
    >
      <div className="field">
        <label htmlFor="dispute-message">What's wrong, and what's your evidence?</label>
        <textarea id="dispute-message" className="textarea" required minLength={10} maxLength={4000} value={message} onChange={(e) => setMessage(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="dispute-contact">Contact (optional)</label>
        <input id="dispute-contact" className="input" maxLength={200} value={contact} onChange={(e) => setContact(e.target.value)} placeholder="Email or @handle" />
      </div>
      {state.status === "error" && <p className="form-error" role="alert">{state.message}</p>}
      <div className="form-row">
        <button className="btn btn-primary" type="submit" disabled={state.status === "sending"}>
          {state.status === "sending" ? "Sending…" : "Send dispute"}
        </button>
      </div>
    </form>
  );
}
