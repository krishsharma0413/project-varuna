import { keepPreviousData, useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { type FormEvent, type ReactNode, useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { api } from "../api/client";
import type { BusinessCriticalRow, LogRow, LogsResponse } from "../api/types";
import { useAuth } from "../auth/AuthProvider";
import { GoogleSignIn } from "../auth/GoogleSignIn";
import { ErrorNotice, SectionHead } from "../components/ui";
import { NotFound } from "./Method";

const PRESETS = ["15m", "30m", "1h", "6h", "24h", "7d", "30d"];
const LEVELS = ["debug", "info", "error"] as const;
const SOURCES = ["api", "worker"];
const TRACE_ID = /^[0-9a-f]{32}$/i;

const timeFormat = new Intl.DateTimeFormat("en-IN", {
  day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
});

export function localTime(iso: string): string {
  const date = new Date(iso);
  return `${timeFormat.format(date)}.${String(date.getMilliseconds()).padStart(3, "0")}`;
}

/** datetime-local value (local time) <-> ISO (UTC). */
function toIso(local: string): string {
  return local ? new Date(local).toISOString() : "";
}
function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function AdminLogs() {
  return <AdminGate>{(email) => <LogsViewer email={email} />}</AdminGate>;
}

/** Sign-in prompt for visitors, 404 for signed-in non-admins, the page for admins. */
export function AdminGate({ children }: { children: (email: string) => ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) {
    return <section className="sec"><div className="wrap"><div className="skeleton" style={{ height: 240 }} aria-busy="true" /></div></section>;
  }
  if (!me?.email) {
    return (
      <section className="sec">
        <div className="wrap">
          <meta name="robots" content="noindex" />
          <div className="notice">
            <h3>Sign in</h3>
            <p style={{ marginBottom: 18 }}>This page is private.</p>
            <GoogleSignIn />
          </div>
        </div>
      </section>
    );
  }
  if (!me.is_admin) return <NotFound />;
  return children(me.email);
}

function LogsViewer({ email }: { email: string }) {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "critical" ? "critical" : "logs";
  const setParam = (changes: Record<string, string | null>) => {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    setParams(next, { replace: true, preventScrollReset: true });
  };

  return (
    <>
      <title>Logs · varuna</title>
      <meta name="robots" content="noindex" />
      <section className="sec">
        <div className="wrap">
          <SectionHead num="⌘" title={<>Logs <em>private</em></>} sub={`Visible only to admins. Signed in as ${email}. Times are shown in your local time zone.`} />
          <div className="chips" role="tablist" aria-label="Log type" style={{ marginBottom: 24 }}>
            <button type="button" role="tab" className="chip" aria-pressed={tab === "logs"} onClick={() => setParam({ tab: null })}>Logs</button>
            <button type="button" role="tab" className="chip" aria-pressed={tab === "critical"} onClick={() => setParam({ tab: "critical" })}>Business critical</button>
          </div>
          <Filters params={params} setParam={setParam} tab={tab} />
          {tab === "logs" ? <LogResults params={params} setParam={setParam} /> : <CriticalResults params={params} setParam={setParam} />}
        </div>
      </section>
    </>
  );
}

type SetParam = (changes: Record<string, string | null>) => void;

function Filters({ params, setParam, tab }: { params: URLSearchParams; setParam: SetParam; tab: string }) {
  const search = params.get("trace") || params.get("reel") || "";
  const [draft, setDraft] = useState(search);
  const [text, setText] = useState(params.get("q") ?? "");
  const preset = params.get("since") ? "custom" : params.get("preset") ?? "30m";
  const [custom, setCustom] = useState({ since: toLocalInput(params.get("since")), until: toLocalInput(params.get("until")) });
  const levels = (params.get("levels") ?? "").split(",").filter(Boolean);
  const sources = (params.get("sources") ?? "").split(",").filter(Boolean);
  const searching = Boolean(search);

  useEffect(() => setDraft(search), [search]);
  const sinceParam = params.get("since");
  const untilParam = params.get("until");
  useEffect(() => setCustom({ since: toLocalInput(sinceParam), until: toLocalInput(untilParam) }), [sinceParam, untilParam]);

  const submitSearch = (e: FormEvent) => {
    e.preventDefault();
    const value = draft.trim();
    if (!value) return setParam({ trace: null, reel: null });
    if (TRACE_ID.test(value)) setParam({ trace: value.toLowerCase(), reel: null, tab: null });
    else setParam({ reel: value, trace: null, tab: null });
  };
  const toggle = (key: "levels" | "sources", current: string[], value: string) => {
    const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
    setParam({ [key]: next.join(",") || null });
  };

  return (
    <div className="admin-filters">
      {tab === "logs" && (
        <form className="admin-row" onSubmit={submitSearch}>
          <label className="search" style={{ maxWidth: 560 }}>
            <span className="sr-only">Trace ID, reel link or reel ID</span>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Trace ID, reel link or reel ID" />
          </label>
          <button className="btn btn-primary btn-sm" type="submit">Find</button>
          {searching && <button className="btn btn-ghost btn-sm" type="button" onClick={() => setParam({ trace: null, reel: null })}>Clear</button>}
        </form>
      )}

      <div className="admin-row" aria-disabled={searching && tab === "logs"}>
        <span className="mini-label admin-label">Time</span>
        <div className="chips">
          {PRESETS.map((p) => (
            <button key={p} type="button" className="chip" aria-pressed={preset === p} disabled={searching && tab === "logs"}
              onClick={() => setParam({ preset: p === "30m" ? null : p, since: null, until: null })}>
              Last {p}
            </button>
          ))}
          <button type="button" className="chip" aria-pressed={preset === "custom"} disabled={searching && tab === "logs"}
            onClick={() => setParam({ since: toIso(custom.since) || new Date(Date.now() - 3_600_000).toISOString(), preset: null })}>
            Custom
          </button>
        </div>
      </div>
      {preset === "custom" && !(searching && tab === "logs") && (
        <form className="admin-row" onSubmit={(e) => { e.preventDefault(); setParam({ since: toIso(custom.since) || null, until: toIso(custom.until) || null }); }}>
          <label className="field admin-date"><span className="mini-label">From</span>
            <input className="input" type="datetime-local" value={custom.since} onChange={(e) => setCustom({ ...custom, since: e.target.value })} required />
          </label>
          <label className="field admin-date"><span className="mini-label">To (optional)</span>
            <input className="input" type="datetime-local" value={custom.until} onChange={(e) => setCustom({ ...custom, until: e.target.value })} />
          </label>
          <button className="btn btn-primary btn-sm" type="submit">Apply</button>
        </form>
      )}
      {searching && tab === "logs" && <p className="hint">Searching by ID shows whole journeys, so the time range doesn't apply.</p>}

      {tab === "logs" && (
        <div className="admin-row">
          <span className="mini-label admin-label">Level</span>
          <div className="chips">
            {LEVELS.map((l) => <button key={l} type="button" className="chip" aria-pressed={levels.includes(l)} onClick={() => toggle("levels", levels, l)}>{l}</button>)}
          </div>
          <span className="mini-label admin-label">Source</span>
          <div className="chips">
            {SOURCES.map((s) => <button key={s} type="button" className="chip" aria-pressed={sources.includes(s)} onClick={() => toggle("sources", sources, s)}>{s}</button>)}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); setParam({ q: text.trim() || null }); }} style={{ flex: "1 1 220px" }}>
            <label className="search" style={{ maxWidth: 360 }}>
              <span className="sr-only">Message contains</span>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Message contains… (Enter)" />
            </label>
          </form>
        </div>
      )}
    </div>
  );
}

function logQuery(params: URLSearchParams, before?: string): string {
  const q = new URLSearchParams();
  for (const key of ["preset", "since", "until", "levels", "sources", "q"]) {
    const value = params.get(key);
    if (value) q.set(key, value);
  }
  const trace = params.get("trace");
  const reel = params.get("reel");
  if (trace) q.set("trace_id", trace);
  else if (reel) q.set("reel", reel);
  if (before) q.set("before", before);
  return q.toString();
}

function LogResults({ params, setParam }: { params: URLSearchParams; setParam: SetParam }) {
  const [live, setLive] = useState(false);
  const key = logQuery(params);
  const query = useInfiniteQuery({
    queryKey: ["admin-logs", key],
    queryFn: ({ pageParam }) => api<LogsResponse>(`/admin/logs?${logQuery(params, pageParam || undefined)}`),
    initialPageParam: "",
    getNextPageParam: (last) => last.next_before ?? undefined,
    placeholderData: keepPreviousData,
    refetchInterval: live ? 10_000 : false,
  });

  if (query.isPending) return <div className="skeleton" style={{ height: 320 }} aria-busy="true" />;
  if (query.error) return <ErrorNotice error={query.error} retry={() => void query.refetch()} />;

  const first = query.data.pages[0];
  const rows = query.data.pages.flatMap((p) => p.items);
  const summary =
    first.mode === "trace" ? `Journey of trace ${params.get("trace")}`
    : first.mode === "reel" ? `Reel ${first.reel_id}: ${first.trace_ids.length} ${first.trace_ids.length === 1 ? "journey" : "journeys"}`
    : `Newest first${first.since ? ` since ${localTime(first.since)}` : ""}${first.until ? ` until ${localTime(first.until)}` : ""}`;

  return (
    <>
      <div className="admin-row admin-summary">
        <strong>{rows.length} {rows.length === 1 ? "line" : "lines"}</strong>
        <span>{summary}</span>
        <span style={{ marginLeft: "auto", display: "inline-flex", gap: 10 }}>
          {first.mode === "range" && (
            <label className="admin-live"><input type="checkbox" checked={live} onChange={(e) => setLive(e.target.checked)} /> Auto-refresh</label>
          )}
          <button className="btn btn-ghost btn-sm" onClick={() => void query.refetch()} disabled={query.isFetching}>
            {query.isFetching ? "Loading…" : "Refresh"}
          </button>
        </span>
      </div>
      {rows.length === 0 ? (
        <div className="notice notice-dashed"><h3>No log lines</h3><p>Nothing matches these filters.</p></div>
      ) : (
        <LogTable rows={rows} onTrace={(trace) => setParam({ trace, reel: null })} />
      )}
      {query.hasNextPage && (
        <div className="load-more">
          <button className="btn btn-ghost" disabled={query.isFetchingNextPage} onClick={() => void query.fetchNextPage()}>
            {query.isFetchingNextPage ? "Loading…" : "Load older"}
          </button>
        </div>
      )}
    </>
  );
}

function LogTable({ rows, onTrace }: { rows: LogRow[]; onTrace: (trace: string) => void }) {
  return (
    <div className="table-scroll">
      <table className="log-table">
        <thead><tr><th scope="col">Time</th><th scope="col">Level</th><th scope="col">Trace</th><th scope="col">Message</th></tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={`${row.timestamp}-${i}`} data-level={row.log_level}>
              <td className="log-time">{localTime(row.timestamp)}</td>
              <td><span className="log-level" data-level={row.log_level}>{row.log_level}</span></td>
              <td>
                {row.trace_id && row.trace_id !== "-" ? (
                  <button type="button" className="log-trace" title={row.trace_id} onClick={() => onTrace(row.trace_id)}>{row.trace_id.slice(0, 8)}</button>
                ) : "—"}
              </td>
              <td className="log-message">{row.message}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CriticalResults({ params, setParam }: { params: URLSearchParams; setParam: SetParam }) {
  const q = new URLSearchParams();
  for (const key of ["preset", "since", "until"]) {
    const value = params.get(key);
    if (value) q.set(key, value);
  }
  const query = useQuery({
    queryKey: ["admin-critical", q.toString()],
    queryFn: () => api<{ items: BusinessCriticalRow[] }>(`/admin/business-critical?${q}`),
    placeholderData: keepPreviousData,
  });
  if (query.isPending) return <div className="skeleton" style={{ height: 240 }} aria-busy="true" />;
  if (query.error) return <ErrorNotice error={query.error} retry={() => void query.refetch()} />;
  const rows = query.data.items;
  return (
    <>
      <div className="admin-row admin-summary">
        <strong>{rows.length} {rows.length === 1 ? "event" : "events"}</strong>
        <span>When a search engine started failing or recovered.</span>
        <button className="btn btn-ghost btn-sm" style={{ marginLeft: "auto" }} onClick={() => void query.refetch()}>Refresh</button>
      </div>
      {rows.length === 0 ? (
        <div className="notice notice-dashed"><h3>Nothing in this range</h3><p>No search engine changed state.</p></div>
      ) : (
        <div className="table-scroll">
          <table className="log-table">
            <thead><tr><th scope="col">Time</th><th scope="col">Engine</th><th scope="col">Event</th><th scope="col">Trace</th><th scope="col">Detail</th></tr></thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={`${row.timestamp}-${i}`}>
                  <td className="log-time">{localTime(row.timestamp)}</td>
                  <td className="log-message">{row.search_engine}</td>
                  <td><span className="log-level" data-level={row.event === "failing" ? "error" : "info"}>{row.event}</span></td>
                  <td>
                    {row.trace_id && row.trace_id !== "-" ? (
                      <button type="button" className="log-trace" title={row.trace_id}
                        onClick={() => setParam({ tab: null, trace: row.trace_id, reel: null })}>{row.trace_id.slice(0, 8)}</button>
                    ) : "—"}
                  </td>
                  <td className="log-message">{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
