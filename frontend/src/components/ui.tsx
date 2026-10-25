import type { ReactNode } from "react";
import { Link } from "react-router";
import { ApiError } from "../api/client";
import type { Verdict } from "../api/types";
import { VERDICT_ORDER, VERDICTS } from "../lib/verdicts";

export function VerdictBadge({ verdict, large = false }: { verdict: Verdict; large?: boolean }) {
  const meta = VERDICTS[verdict];
  return (
    <span className={large ? "verdict verdict-lg" : "verdict"} data-v={verdict}>
      <i aria-hidden="true">{meta.glyph}</i>
      {meta.label}
    </span>
  );
}

export function SectionHead({ num, title, sub }: { num: string; title: ReactNode; sub?: ReactNode }) {
  return (
    <header className="sec-head">
      <span className="sec-num" aria-hidden="true">{num}</span>
      <h2 className="sec-title">{title}</h2>
      {sub && <p className="sec-sub">{sub}</p>}
    </header>
  );
}

export function ErrorNotice({ error, retry }: { error: unknown; retry?: () => void }) {
  const message = error instanceof ApiError ? error.message : "Something went wrong loading this.";
  return (
    <div className="notice notice-dashed" role="alert">
      <h3>Couldn't load this</h3>
      <p>{message}</p>
      {retry && <button className="btn btn-ghost btn-sm" onClick={retry}>Try again</button>}
    </div>
  );
}

export function EmptyNotice({ title, children, cta = true }: { title: string; children: ReactNode; cta?: boolean }) {
  return (
    <div className="notice">
      <h3>{title}</h3>
      <p>{children}</p>
      {cta && <Link className="btn btn-primary btn-sm" to="/check">Check a reel</Link>}
    </div>
  );
}

export function SkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="reel-grid" aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }, (_, i) => <div key={i} className="skeleton skeleton-card" />)}
    </div>
  );
}

export function VerdictLegend() {
  return (
    <ul className="legend">
      {VERDICT_ORDER.map((v) => (
        <li key={v}>
          <div><VerdictBadge verdict={v} /></div>
          <p>{VERDICTS[v].description}</p>
        </li>
      ))}
    </ul>
  );
}

export function SearchIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="7" cy="7" r="5" />
      <path d="m11 11 3.5 3.5" />
    </svg>
  );
}
