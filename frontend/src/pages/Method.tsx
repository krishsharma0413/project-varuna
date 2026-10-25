import { Link } from "react-router";
import { usePublicConfig, useRankings } from "../api/hooks";
import { ErrorNotice, SectionHead, VerdictLegend } from "../components/ui";

export function Method() {
  const rankings = useRankings();
  const { data: config } = usePublicConfig();
  const minSources = config?.min_independent_sources ?? 2;
  return (
    <>
      <section className="sec">
        <div className="wrap">
          <SectionHead
            num="01"
            title={<>How we <em>check</em></>}
            sub={<>Every verdict shows its sources. We judge claims, not people. The exact models, settings and prompts in use are on the <Link className="underline" to="/transparency">transparency page</Link>.</>}
          />
          <div className="prose">
            <h3>1. Read the whole reel</h3>
            <p>The video is downloaded, speech is transcribed, on-screen text is read from frames, and the caption is added. A small model merges these into one clean text. Video and frames are deleted afterwards; only text is kept.</p>
            <h3>2. Split it into claims</h3>
            <p>Each checkable statement becomes its own claim. Claims are classified as verifiable facts, contested claims, opinions or predictions. Opinions are not judged, and predictions are checked again when they fall due.</p>
            <h3>3. Check in three tiers</h3>
            <ul>
              <li><strong>Tier 1:</strong> official and primary sources such as government notices, gazettes and court orders.</li>
              <li><strong>Tier 2:</strong> existing fact-checks from established fact-checkers.</li>
              <li><strong>Tier 3:</strong> independent web search, with every source weighted by its credibility rank.</li>
            </ul>
            <h3>4. Resolve conflicts by rank</h3>
            <p>When sources disagree, the higher-ranked source wins. True or False needs at least {minSources} independent sources. If the evidence conflicts and rank doesn't settle it, the claim is marked Unverified instead of guessed. On contested political claims the government is one source, not the final word.</p>
            <h3>5. Expire and re-check</h3>
            <p>Every result has a re-check date that depends on how fast the subject moves: hours for breaking news, days for ongoing stories, weeks for settled events. After that date, the next request checks the reel again and the old result moves into its history, so you can see how a verdict changed.</p>
          </div>
        </div>
      </section>
      <section className="sec">
        <div className="wrap">
          <SectionHead num="02" title={<>The <em>verdicts</em></>} />
          <VerdictLegend />
        </div>
      </section>
      <section className="sec" id="sources">
        <div className="wrap">
          <SectionHead num="03" title={<>Source <em>rankings</em></>} sub="Ranked by hand, public and versioned, so anyone can see why a source sits where it does. Unlisted sources get the lowest rank." />
          {rankings.error ? (
            <ErrorNotice error={rankings.error} />
          ) : (
            <>
              {rankings.data && Object.keys(rankings.data.ranks ?? {}).length > 0 && (
                <ul className="legend" style={{ marginBottom: 32 }}>
                  {Object.entries(rankings.data.ranks).map(([rank, meaning]) => (
                    <li key={rank}><div><span className="verdict">Rank {rank}</span></div><p>{meaning}</p></li>
                  ))}
                </ul>
              )}
              <div className="table-scroll">
                <table className="board">
                  <thead><tr><th scope="col">Domain</th><th scope="col">Rank</th><th scope="col">Kind</th><th scope="col">Why</th></tr></thead>
                  <tbody>
                    {rankings.data?.sources.map((s) => (
                      <tr key={s.domain}><td>{s.domain}</td><td>{s.rank}</td><td>{s.kind}</td><td>{s.rationale}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          <p className="note">Think a ranking is wrong? The ranking file is part of the open-source repository. <Link to="/check">Disputes</Link> about single verdicts go on each result page.</p>
        </div>
      </section>
    </>
  );
}

export function NotFound() {
  return (
    <section className="sec">
      <div className="wrap">
        <SectionHead num="404" title={<>Not <em>found</em></>} sub="That page doesn't exist." />
        <Link className="btn btn-primary" to="/">Back to latest checks</Link>
      </div>
    </section>
  );
}
