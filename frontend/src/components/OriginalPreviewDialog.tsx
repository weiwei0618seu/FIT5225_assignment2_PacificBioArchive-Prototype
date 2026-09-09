import { useEffect } from "react";

type Props = {
  url: string;
  title: string;
  mediaType?: string | null;
  onClose: () => void;
};

function shouldRenderVideo(url: string, mediaType?: string | null) {
  if (mediaType === "video") return true;
  if (mediaType === "image") return false;
  return /\.(mp4|mov|avi|webm|m4v)(?:$|[?#])/i.test(url);
}

export function OriginalPreviewDialog({ url, title, mediaType, onClose }: Props) {
  const isVideo = shouldRenderVideo(url, mediaType);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }

    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div className="preview-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="preview-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="original-preview-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="preview-panel__header">
          <div>
            <p className="eyebrow">Original media</p>
            <h2 id="original-preview-title">{title}</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Close original preview" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="preview-panel__stage">
          {isVideo ? (
            <video src={url} controls preload="metadata">
              Your browser cannot play this video preview.
            </video>
          ) : (
            <img src={url} alt={`Original preview of ${title}`} />
          )}
        </div>

        <p className="preview-panel__hint">
          The original file is shown inside Pacific BioArchive, so the demo stays on this page. Press Esc or Close to return.
        </p>

        <div className="preview-panel__actions">
          <button className="button button--primary" type="button" onClick={onClose}>
            Close preview
          </button>
        </div>
      </section>
    </div>
  );
}
