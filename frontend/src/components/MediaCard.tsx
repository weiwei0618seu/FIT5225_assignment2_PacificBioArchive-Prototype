import { useState } from "react";

import type { MediaRecord } from "../api/types";
import { OriginalPreviewDialog } from "./OriginalPreviewDialog";

type Props = {
  media: MediaRecord;
  selectable?: boolean;
  selected?: boolean;
  onSelectedChange?: (selected: boolean) => void;
  compact?: boolean;
};

export function MediaCard({ media, selectable = false, selected = false, onSelectedChange, compact = false }: Props) {
  const [previewingOriginal, setPreviewingOriginal] = useState(false);
  const preview = media.thumbnail_url || (media.file_type === "image" ? media.original_url : null);
  return (
    <>
      <article className={`media-card${compact ? " media-card--compact" : ""}${selected ? " media-card--selected" : ""}`}>
        <div className="media-card__preview">
          {preview ? (
            <img src={preview} alt={`Preview of ${media.filename}`} />
          ) : (
            <div className="video-placeholder" aria-label="Video result">
              <span aria-hidden="true">▶</span><small>VIDEO</small>
            </div>
          )}
          {selectable && (
            <label className="media-select">
              <input
                type="checkbox"
                checked={selected}
                onChange={(event) => onSelectedChange?.(event.target.checked)}
              />
              Select
            </label>
          )}
        </div>
        <div className="media-card__body">
          <div className="media-card__heading">
            <div><p className="eyebrow">{media.file_type}</p><h3>{media.filename}</h3></div>
            <span className="ready-badge">Ready</span>
          </div>
          {Object.keys(media.species_counts).length ? (
            <dl className="species-counts">
              {Object.entries(media.species_counts).map(([species, count]) => (
                <div key={species}><dt>{species}</dt><dd>{count}</dd></div>
              ))}
            </dl>
          ) : <p className="empty-copy">No target wildlife was detected.</p>}
          <div className="tag-list" aria-label="Media tags">
            {media.all_tags.map((tag) => <span key={tag}>{tag}</span>)}
          </div>
          <div className="media-meta">
            <span>Model {media.model_version || "not reported"}</span>
            {media.video_samples != null && <span>{media.video_samples} sampled frames</span>}
          </div>
          {media.original_url && (
            <button className="button button--outline" type="button" onClick={() => setPreviewingOriginal(true)}>
              Open original
            </button>
          )}
        </div>
      </article>
      {previewingOriginal && media.original_url && (
        <OriginalPreviewDialog
          url={media.original_url}
          title={media.filename}
          mediaType={media.file_type}
          onClose={() => setPreviewingOriginal(false)}
        />
      )}
    </>
  );
}
