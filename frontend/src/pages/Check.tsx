import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { ApiError, api } from "../api/client";
import { useJob, usePublicConfig } from "../api/hooks";
import type { SubmitResult } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { GoogleSignIn } from "../auth/GoogleSignIn";
import { ErrorNotice, SectionHead } from "../components/ui";

const REEL_URL = /^(?:https?:\/\/)?(?:www\.|m\.)?instagram\.com\/(?:[A-Za-z0-9_.]+\/)?(?:reels?|p|tv)\/[A-Za-z0-9_-]{5,40}/i;

export function Check() {
  const { me, loading } = useAuth();
  return (
    <section className="sec">
      <div className="wrap">
        <SectionHead
          num="01"
          title={<>Check <em>a reel</em></>}
          sub="Paste an Instagram reel link. We download it, read everything it says, and check each claim against ranked sources."
        />
        {loading ? (
          <div className="skeleton" style={{ height: 160, maxWidth: 760 }} aria-busy="true" />
        ) : me?.email && me.invited ? (
          <SubmitForm />
        ) : (
          <div className="notice">
            <h3>Invite only, for now</h3>
            <p style={{ marginBottom: 18 }}>
              {me?.email
                ? "Your email isn't on the invite list yet."
                : "Sign in with the Google account you were invited with. Reading results stays open to everyone."}
            </p>
            <GoogleSignIn />
          </div>
        )}
      </div>
    </section>
  );
}

function SubmitForm() {
  const navigate = useNavigate();
  const { data: config } = usePublicConfig();
  const [params] = useSearchParams();
  const [url, setUrl] = useState(params.get("url") ?? "");
  const [error, setError] = useState<string | null>(null);
  const [rejected, setRejected] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const topics = config?.topics ?? [];

  return (
    <form
      className="form"
      noValidate
      onSubmit={async (e) => {
        e.preventDefault();
        if (!REEL_URL.test(url.trim())) {
          setError("That doesn't look like an Instagram reel link. It should look like instagram.com/reel/…");
          return;
        }
        setError(null);
        setRejected(null);
        setSending(true);
        try {
          const result = await api<SubmitResult>("/submissions", { method: "POST", body: JSON.stringify({ reel_url: url.trim() }) });
          if (result.status === "rejected") {
            setRejected(result.reason || "This reel isn't about a topic we check.");
            setSending(false);
            return;
          }
          navigate(result.status === "done" || !result.job_id ? `/r/${result.reel_id}` : `/check/${result.job_id}`);
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "Couldn't submit. Please try again.");
          setSending(false);
        }
      }}
    >
      {topics.length > 0 && <TopicList topics={topics} />}
      <div className="field">
        <label htmlFor="reel-url">Reel link</label>
        <input
          id="reel-url"
          className="input"
          type="url"
          inputMode="url"
          autoComplete="off"
          placeholder="https://www.instagram.com/reel/…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
      </div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {rejected && (
        <div className="notice notice-dashed" role="alert">
          <h3>Not checked: off-topic</h3>
          <p>{rejected} We only check reels about the topics listed above, so nothing was spent on this one.</p>
        </div>
      )}
      <div className="form-row">
        <button className="btn btn-primary" type="submit" disabled={sending}>{sending ? "Submitting…" : "Start check"}</button>
        <p className="hint">
          Limits: {config?.submit_limits.join(", ") ?? "a few per hour"} per account; reels up to{" "}
          {config ? Math.round(config.max_video_seconds / 60) : 3} minutes. If someone already asked about this reel,
          you'll get the same result.
        </p>
      </div>
    </form>
  );
}

function TopicList({ topics }: { topics: string[] }) {
  return (
    <div className="field">
      <span className="mini-label">Reels we check right now</span>
      <div className="chips">
        {topics.map((t) => <span key={t} className="chip chip-static">{t}</span>)}
      </div>
      <p className="hint">The reel's caption is checked against these topics first. Off-topic reels are turned away before anything is downloaded.</p>
    </div>
  );
}

const STAGES = ["Queued", "Checking topic", "Downloading", "Reading the reel", "Checking claims", "Done"];
const STEP_STAGE: Record<string, number> = {
  queued: 0, retrying: 0, metadata: 1, topic_check: 1, download: 2, extract: 3, transcribe: 3, cleanup: 3,
  claims: 4, verify: 4, store: 4, done: 5,
};

export function JobPage() {
  const { jobId = "" } = useParams();
  const { data: job, error, refetch } = useJob(jobId);

  if (error) {
    return <section className="sec"><div className="wrap"><ErrorNotice error={error} retry={() => void refetch()} /></div></section>;
  }
  const finished = job?.status === "done" || job?.status === "failed" || job?.status === "rejected";
  const stage = job ? (job.status === "done" ? 5 : STEP_STAGE[job.step ?? "queued"] ?? (job.status === "rejected" ? 1 : 0)) : 0;
  return (
    <section className="sec">
      <div className="wrap">
        <SectionHead num="01" title={<>Checking <em>the reel</em></>} sub="This usually takes a minute or two. You can leave this page; the result will appear on the reel's page." />
        <ol className="job" aria-live="polite">
          {STAGES.map((label, index) => (
            <li key={label} className={[index <= stage ? "on" : "", index === stage && !finished ? "now" : ""].join(" ")}>
              {label}
            </li>
          ))}
        </ol>
        {job?.status === "done" && (
          <p className="job-status">Done. <Link className="underline" to={`/r/${job.reel_id}`}>View the result →</Link></p>
        )}
        {job?.status === "failed" && (
          <div className="notice notice-dashed" style={{ marginTop: 28 }} role="alert">
            <h3>The check failed</h3>
            <p>{job.error ?? "Something went wrong."}</p>
            <Link className="btn btn-ghost btn-sm" to="/check">Try another reel</Link>
          </div>
        )}
        {job?.status === "rejected" && (
          <div className="notice notice-dashed" style={{ marginTop: 28 }} role="alert">
            <h3>Not checked: off-topic</h3>
            <p>{job.error ?? "This reel isn't about a topic we check."} Nothing was downloaded or transcribed, and it doesn't count against today's limit.</p>
            <Link className="btn btn-ghost btn-sm" to="/transparency">See the topics we check</Link>
          </div>
        )}
        {job && !finished && job.error && <p className="job-status">{job.error}</p>}
      </div>
    </section>
  );
}
