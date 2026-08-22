import type { MediaRecord } from "../api/types";
import { MediaCard } from "./MediaCard";

type Props = {
  media: MediaRecord[];
  total: number;
  truncated?: boolean;
};

export function MediaResults({ media, total, truncated = false }: Props) {
  return (
    <section className="results-section" aria-labelledby="results-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Query result</p><h2 id="results-heading">{total} {total === 1 ? "record" : "records"}</h2></div>
        {truncated && <span className="secure-pill">First {media.length} shown</span>}
      </div>
      {media.length ? (
        <div className="results-grid">
          {media.map((item) => <MediaCard key={item.file_id} media={item} compact />)}
        </div>
      ) : (
        <div className="empty-state"><span aria-hidden="true">○</span><h3>No matching wildlife yet</h3><p>Try fewer requirements, a lower count, or another reference image.</p></div>
      )}
    </section>
  );
}
