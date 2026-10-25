import type { ClaimResult } from "../api/types";
import { CLAIM_TYPES } from "../lib/verdicts";
import { VerdictBadge } from "./ui";

const STANCE: Record<string, string> = { supports: "supports it", contradicts: "contradicts it", related: "background" };
const DELIVERY: Record<string, string> = { sarcastic: "said sarcastically", hyperbole: "exaggerated in the reel", quoted: "quoting someone" };

export function ClaimTable({ claims }: { claims: ClaimResult[] }) {
  if (!claims.length) {
    return <p className="hint" style={{ padding: "18px 0" }}>No checkable claims were found in this reel.</p>;
  }
  return (
    <div className="table-scroll">
      <table className="check-table">
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Claimed in the reel</th>
            <th scope="col">Verdict</th>
            <th scope="col">What the sources say</th>
            <th scope="col">Sources</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim, index) => (
            <tr key={claim.claim_id}>
              <td className="c-n">{String(index + 1).padStart(2, "0")}</td>
              <td className="c-claim" data-label="Claimed in the reel">
                {claim.text}
                <span className="c-type">
                  {CLAIM_TYPES[claim.type]}
                  {claim.delivery && DELIVERY[claim.delivery] ? ` · ${DELIVERY[claim.delivery]}` : ""}
                  {claim.original && claim.original !== claim.text ? ` · “${claim.original}”` : ""}
                </span>
              </td>
              <td data-label="Verdict"><VerdictBadge verdict={claim.verdict} /></td>
              <td className="c-says" data-label="What the sources say">{claim.explanation}</td>
              <td data-label="Sources">
                {claim.sources.length ? (
                  <ul className="src-list">
                    {claim.sources.map((s) => (
                      <li key={s.url}>
                        <span className="tier" title={`Tier ${s.tier}`}>T{s.tier}</span>
                        <span>
                          <a href={s.url} target="_blank" rel="noopener noreferrer nofollow">{s.domain}</a>{" "}
                          <small>{s.kind} · rank {s.rank}{s.published ? ` · ${s.published}` : ""}{s.stance ? ` · ${STANCE[s.stance]}` : ""}</small>
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="hint">No sources</span>
                )}
                {claim.queries && claim.queries.length > 0 && (
                  <details className="src-queries">
                    <summary>
                      {claim.queries.length} {claim.queries.length === 1 ? "search" : "searches"}
                      {claim.search_rounds && claim.search_rounds > 1 ? ` in ${claim.search_rounds} rounds` : ""}
                    </summary>
                    <ul>{claim.queries.map((q) => <li key={q}>{q}</li>)}</ul>
                  </details>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
