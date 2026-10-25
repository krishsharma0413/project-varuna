import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Fragment, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { ApiError, api } from "../api/client";
import type { DeletePlan, RecordDetail, RecordRow } from "../api/types";
import { ErrorNotice, SectionHead, VerdictBadge } from "../components/ui";
import { AdminGate, localTime } from "./AdminLogs";

const STATE_LABEL: Record<RecordRow["state"], string> = {
  checked: "checked",
  stale: "expired",
  rejected: "off-topic",
  empty: "no result",
};

export function AdminRecords() {
  return <AdminGate>{(email) => <RecordsViewer email={email} />}</AdminGate>;
}

function RecordsViewer({ email }: { email: string }) {
  const [params, setParams] = useSearchParams();
  const search = params.get("q") ?? "";
  const open = params.get("open");
  const [draft, setDraft] = useState(search);
  const [deleted, setDeleted] = useState<{ plan: DeletePlan; permalink: string | null } | null>(null);
  useEffect(() => setDraft(search), [search]);

  const setParam = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setParams(next, { replace: true, preventScrollReset: true });
  };

  const query = useQuery({
    queryKey: ["admin-records", search],
    queryFn: () => api<{ items: RecordRow[]; total: number }>(`/admin/reels?${new URLSearchParams(search ? { q: search } : {})}`),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <title>Records · varuna</title>
      <meta name="robots" content="noindex" />
      <section className="sec">
        <div className="wrap">
          <SectionHead num="⌘" title={<>Records <em>private</em></>}
            sub={`Stored reel results. Delete one to check the reel again from scratch and compare. Signed in as ${email}.`} />

          <form className="admin-filters admin-row" onSubmit={(e) => { e.preventDefault(); setParam({ q: draft.trim() || null, open: null }); }}>
            <label className="search" style={{ maxWidth: 560 }}>
              <span className="sr-only">Reel link, reel ID or creator</span>
              <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Reel link, reel ID or creator" />
            </label>
            <button className="btn btn-primary btn-sm" type="submit">Find</button>
            {search && <button className="btn btn-ghost btn-sm" type="button" onClick={() => setParam({ q: null, open: null })}>Clear</button>}
          </form>

          {deleted && (
            <div className="notice" role="status" style={{ marginBottom: 24 }}>
              <h3>Deleted {deleted.plan.reel_id}</h3>
              <p>{describePlan(deleted.plan)}</p>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                <Link className="btn btn-primary btn-sm" to={`/check?url=${encodeURIComponent(deleted.permalink ?? `https://www.instagram.com/reel/${deleted.plan.reel_id}/`)}`}>
                  Check it again
                </Link>
                <Link className="btn btn-ghost btn-sm" to={`/admin/logs?reel=${encodeURIComponent(deleted.plan.reel_id)}`}>Old run's logs</Link>
                <button className="btn btn-ghost btn-sm" type="button" onClick={() => setDeleted(null)}>Dismiss</button>
              </div>
            </div>
          )}

          {query.isPending ? (
            <div className="skeleton" style={{ height: 320 }} aria-busy="true" />
          ) : query.error ? (
            <ErrorNotice error={query.error} retry={() => void query.refetch()} />
          ) : (
            <>
              <div className="admin-row admin-summary">
                <strong>{query.data.items.length} of {query.data.total} {query.data.total === 1 ? "reel" : "reels"}</strong>
                <span>Most recent activity first.</span>
                <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto" }} onClick={() => void query.refetch()} disabled={query.isFetching}>
                  {query.isFetching ? "Loading…" : "Refresh"}
                </button>
              </div>
              {query.data.items.length === 0 ? (
                <div className="notice notice-dashed"><h3>No records</h3><p>{search ? "Nothing matches this search." : "No reel has been stored yet."}</p></div>
              ) : (
                <div className="table-scroll">
                  <table className="log-table records-table">
                    <thead>
                      <tr>
                        <th scope="col">Reel</th><th scope="col">Creator</th><th scope="col">State</th><th scope="col">Verdict</th>
                        <th scope="col">Claims</th><th scope="col">History</th><th scope="col">Requests</th><th scope="col">Last activity</th>
                        <th scope="col"><span className="sr-only">Actions</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {query.data.items.map((row) => (
                        <Fragment key={row.reel_id}>
                          <tr aria-expanded={open === row.reel_id}>
                            <td className="log-message">
                              {row.state === "checked" || row.state === "stale"
                                ? <Link className="underline" to={`/r/${row.reel_id}`}>{row.reel_id}</Link>
                                : row.reel_id}
                            </td>
                            <td>{row.creator_handle ? `@${row.creator_handle}` : "—"}</td>
                            <td><span className="log-level" data-level={row.state === "checked" ? "info" : "debug"}>{STATE_LABEL[row.state]}</span></td>
                            <td>{row.summary ? <VerdictBadge verdict={row.summary.verdict} /> : row.gate_reason ? <span className="hint">{row.gate_reason}</span> : "—"}</td>
                            <td>{row.claim_count}</td>
                            <td>{row.history_count}</td>
                            <td>{row.request_count}</td>
                            <td className="log-time">{row.last_activity ? localTime(row.last_activity) : "—"}</td>
                            <td>
                              <button type="button" className="log-trace" onClick={() => setParam({ open: open === row.reel_id ? null : row.reel_id })}>
                                {open === row.reel_id ? "Close" : "Open"}
                              </button>
                            </td>
                          </tr>
                          {open === row.reel_id && (
                            <tr className="record-detail-row">
                              <td colSpan={9}>
                                <RecordPanel reelId={row.reel_id} onDeleted={(plan) => { setDeleted({ plan, permalink: row.permalink }); setParam({ open: null }); }} />
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      </section>
    </>
  );
}

function describePlan(plan: DeletePlan): string {
  const parts = [`the reel document${plan.history_entries ? ` and its ${plan.history_entries} history ${plan.history_entries === 1 ? "entry" : "entries"}` : ""}`];
  if (plan.delete_claims.length) parts.push(`${plan.delete_claims.length} ${plan.delete_claims.length === 1 ? "claim" : "claims"} only this reel made`);
  if (plan.expire_shared_claims.length) {
    parts.push(`this reel from ${plan.expire_shared_claims.length} shared ${plan.expire_shared_claims.length === 1 ? "claim" : "claims"} (their cached verdicts are expired so they get verified again)`);
  }
  if (plan.creator) parts.push(`this result's counts from @${plan.creator}`);
  return `Removes ${parts.join(", ")}. Jobs, requests, disputes and logs are kept.`;
}

function RecordPanel({ reelId, onDeleted }: { reelId: string; onDeleted: (plan: DeletePlan) => void }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [copied, setCopied] = useState(false);
  const query = useQuery({
    queryKey: ["admin-record", reelId],
    queryFn: () => api<RecordDetail>(`/admin/reels/${encodeURIComponent(reelId)}`),
  });
  const remove = useMutation({
    mutationFn: () => api<DeletePlan>(`/admin/reels/${encodeURIComponent(reelId)}`, { method: "DELETE" }),
    onSuccess: (plan) => {
      queryClient.removeQueries({ queryKey: ["admin-record", reelId] });
      void queryClient.invalidateQueries(); // the list here, and any cached public pages showing this reel
      onDeleted(plan);
    },
    onError: () => setConfirming(false),
  });

  if (query.isPending) return <div className="skeleton" style={{ height: 160 }} aria-busy="true" />;
  if (query.error) return <ErrorNotice error={query.error} retry={() => void query.refetch()} />;
  const detail = query.data;
  const json = JSON.stringify(detail.record, null, 2);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="record-panel">
      <div className="record-facts">
        <div><span className="mini-label">Requests</span>{detail.requests}</div>
        <div><span className="mini-label">Disputes</span>{detail.disputes}</div>
        <div><span className="mini-label">Claims</span>{detail.claims.length}</div>
        <div><span className="mini-label">Runs</span>{detail.jobs.length}</div>
      </div>

      {detail.jobs.length > 0 && (
        <div>
          <span className="mini-label">Runs</span>
          <ul className="record-list">
            {detail.jobs.map((job) => (
              <li key={job.job_id}>
                <span className="log-time">{localTime(job.created_at)}</span>{" "}
                <span className="log-level" data-level={job.status === "failed" ? "error" : "info"}>{job.status}</span>{" "}
                {job.trace_id && <Link className="log-trace" to={`/admin/logs?trace=${job.trace_id}`}>logs {job.trace_id.slice(0, 8)}</Link>}
                {job.error && <span className="hint"> {job.error}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {detail.claims.length > 0 && (
        <div>
          <span className="mini-label">Claims</span>
          <ul className="record-list">
            {detail.claims.map((claim) => (
              <li key={claim.claim_id}>{claim.text}{claim.reels > 1 && <span className="hint"> (also in {claim.reels - 1} other {claim.reels === 2 ? "reel" : "reels"})</span>}</li>
            ))}
          </ul>
        </div>
      )}

      <details className="record-json">
        <summary>Raw record</summary>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => void copy()}>{copied ? "Copied" : "Copy JSON"}</button>
        <pre className="prompt">{json}</pre>
      </details>

      <div className="record-delete">
        <p className="hint">{describePlan(detail.plan)}</p>
        {detail.running_job ? (
          <p className="hint"><strong>A check is running for this reel.</strong> Delete it after the run ends.</p>
        ) : confirming ? (
          <div className="admin-row">
            <strong>Delete {reelId} for good? This can't be undone.</strong>
            <button type="button" className="btn btn-primary btn-sm" disabled={remove.isPending} onClick={() => remove.mutate()}>
              {remove.isPending ? "Deleting…" : "Yes, delete"}
            </button>
            <button type="button" className="btn btn-ghost btn-sm" disabled={remove.isPending} onClick={() => setConfirming(false)}>Cancel</button>
          </div>
        ) : (
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setConfirming(true)}>Delete record</button>
        )}
        {remove.error && (
          <p className="hint" role="alert">{remove.error instanceof ApiError ? remove.error.message : "Delete failed."}</p>
        )}
      </div>
    </div>
  );
}
