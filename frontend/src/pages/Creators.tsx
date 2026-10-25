import { Link, useParams } from "react-router";
import { ApiError } from "../api/client";
import { useCreator, useCreators } from "../api/hooks";
import type { Creator } from "../api/types";
import { ReelGrid } from "../components/ReelCard";
import { EmptyNotice, ErrorNotice, SectionHead, SkeletonGrid } from "../components/ui";

function RecordBar({ creator }: { creator: Creator }) {
  const c = creator.counts;
  const parts = [
    ["true", c.true ?? 0], ["false", c.false ?? 0], ["misleading", c.misleading ?? 0], ["unverified", c.unverified ?? 0],
  ] as const;
  const total = parts.reduce((sum, [, n]) => sum + n, 0);
  if (!creator.record_visible || total === 0) {
    return <span className="hint">Needs {creator.min_sample}+ claims ({creator.claims_checked} so far)</span>;
  }
  const label = parts.map(([k, n]) => `${n} ${k}`).join(", ");
  return (
    <div className="record" role="img" aria-label={`${label}, out of ${total}`}>
      {parts.map(([k, n]) => n > 0 && <span key={k} className={`r-${k}`} style={{ width: `${(n / total) * 100}%` }} />)}
    </div>
  );
}

const Note = () => (
  <>
    <div className="record-key" aria-hidden="true">
      <span><i className="r-true" />True</span><span><i className="r-false" />False</span>
      <span><i className="r-misleading" />Misleading</span><span><i className="r-unverified" />Unverified</span>
    </div>
    <p className="note">
      Only reels people ask about get checked, so this sample leans toward doubtful content. These are counts of
      claims, not judgments of people. Creators can dispute any verdict from its result page.
    </p>
  </>
);

export function Creators() {
  const { data, isPending, error, refetch } = useCreators();
  return (
    <section className="sec">
      <div className="wrap">
        <SectionHead num="01" title={<>Creators, <em>by the numbers</em></>} sub={`Claims checked per creator, sorted by volume. A record appears only after ${data?.min_sample ?? 5} checked claims.`} />
        {isPending ? (
          <div className="skeleton" style={{ height: 320 }} aria-busy="true" />
        ) : error ? (
          <ErrorNotice error={error} retry={() => void refetch()} />
        ) : data.items.length === 0 ? (
          <EmptyNotice title="No creators yet">Creators appear here once their reels are checked.</EmptyNotice>
        ) : (
          <>
            <div className="table-scroll">
              <table className="board">
                <thead>
                  <tr>
                    <th scope="col">Creator</th><th scope="col" className="num">Reels</th><th scope="col" className="num">Claims</th>
                    <th scope="col" className="num">True</th><th scope="col" className="num">False</th>
                    <th scope="col" className="num">Misleading</th><th scope="col" className="num">Unverified</th><th scope="col">Record</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.handle}>
                      <td><Link to={`/c/${c.handle}`}>@{c.handle}</Link></td>
                      <td className="num">{c.reels_checked}</td>
                      <td className="num">{c.claims_checked}</td>
                      <td className="num">{c.counts.true ?? 0}</td>
                      <td className="num">{c.counts.false ?? 0}</td>
                      <td className="num">{c.counts.misleading ?? 0}</td>
                      <td className="num">{c.counts.unverified ?? 0}</td>
                      <td><RecordBar creator={c} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Note />
          </>
        )}
      </div>
    </section>
  );
}

export function CreatorPage() {
  const { handle = "" } = useParams();
  const { data, isPending, error, refetch } = useCreator(handle);
  return (
    <section className="sec">
      <div className="wrap">
        {isPending ? (
          <SkeletonGrid />
        ) : error ? (
          error instanceof ApiError && error.status === 404 ? (
            <EmptyNotice title="No checks yet">No reels from @{handle} have been checked.</EmptyNotice>
          ) : (
            <ErrorNotice error={error} retry={() => void refetch()} />
          )
        ) : (
          <>
            <title>{`@${data.creator.handle} · varuna fact checker`}</title>
            <SectionHead
              num="@"
              title={data.creator.handle}
              sub={`${data.creator.reels_checked} reels and ${data.creator.claims_checked} claims checked.`}
            />
            <div style={{ marginBottom: 40 }}>
              <RecordBar creator={data.creator} />
              <Note />
            </div>
            <ReelGrid reels={data.reels} />
          </>
        )}
      </div>
    </section>
  );
}
