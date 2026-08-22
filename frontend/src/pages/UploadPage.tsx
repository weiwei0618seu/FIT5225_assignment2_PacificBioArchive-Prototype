import { type ChangeEvent, useState } from "react";

import { ApiError } from "../api/client";
import type { MediaRecord } from "../api/types";
import { MediaCard } from "../components/MediaCard";
import { StatusMessage } from "../components/StatusMessage";
import {
  ACCEPTED_MEDIA_TYPES,
  uploadAndWait,
  validateMediaFile,
  type UploadProgress,
} from "../upload/uploadWorkflow";

const PHASE_COPY: Record<UploadProgress["phase"], string> = {
  hashing: "Calculating SHA-256 locally…",
  reserving: "Checking for duplicates…",
  uploading: "Uploading directly to private storage…",
  processing: "Detecting and classifying wildlife…",
};

function displayError(error: unknown): string {
  if (error instanceof ApiError && error.code === "DUPLICATE_FILE") {
    return "These exact file bytes already exist in the archive. Choose a different file.";
  }
  if (error instanceof Error) return error.message;
  return "The upload could not be completed. Please try again.";
}

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState<MediaRecord | null>(null);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] || null;
    setFileError("");
    setError("");
    setResult(null);
    setProgress(null);
    if (!selected) {
      setFile(null);
      return;
    }
    try {
      validateMediaFile(selected);
      setFile(selected);
    } catch (caught) {
      setFile(null);
      setFileError(displayError(caught));
      event.target.value = "";
    }
  }

  async function submit() {
    if (!file) {
      setFileError("Choose an image or video first.");
      return;
    }
    setError("");
    setResult(null);
    try {
      setResult(await uploadAndWait(file, setProgress));
      setProgress(null);
    } catch (caught) {
      setError(displayError(caught));
      setProgress(null);
    }
  }

  const busy = progress !== null;
  return (
    <main className="page upload-page">
      <div className="page-heading">
        <div><p className="eyebrow">Private ingest</p><h1>Upload wildlife media</h1></div>
        <span className="secure-pill">10 MiB images · 50 MiB videos</span>
      </div>

      <section className="upload-layout">
        <div className="upload-panel">
          <label className="drop-zone">
            <input
              type="file"
              accept={ACCEPTED_MEDIA_TYPES.join(",")}
              onChange={chooseFile}
              disabled={busy}
            />
            <span className="drop-zone__icon" aria-hidden="true">↑</span>
            <strong>{file ? file.name : "Choose an image or video"}</strong>
            <small>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MiB · ${file.type}` : "JPG, PNG, WebP, MP4, MOV or AVI"}</small>
          </label>
          {fileError && <StatusMessage tone="error">{fileError}</StatusMessage>}
          {error && <StatusMessage tone="error">{error}</StatusMessage>}
          {progress && (
            <div className="upload-progress" role="status" aria-live="polite">
              <div><strong>{PHASE_COPY[progress.phase]}</strong><span>{progress.phase === "uploading" ? `${progress.percent || 0}%` : "Working"}</span></div>
              <progress value={progress.phase === "uploading" ? progress.percent || 0 : undefined} max="100" />
              {progress.fileId && <small>File ID: {progress.fileId}</small>}
            </div>
          )}
          <button className="button button--primary upload-action" type="button" onClick={submit} disabled={!file || busy}>
            {busy ? "Processing…" : "Upload and analyse"}
          </button>
          <p className="privacy-note">Your browser hashes the file first. Duplicate bytes are rejected before storage, and uploads go directly to a private S3 object using short-lived signed headers.</p>
        </div>

        <aside className="upload-guide">
          <p className="eyebrow">What happens next</p>
          <ol>
            <li><span>01</span><div><strong>Verify</strong><p>Type, size and SHA-256 are checked twice.</p></div></li>
            <li><span>02</span><div><strong>Analyse</strong><p>Images are thumbnailed; videos sample exactly one frame per second.</p></div></li>
            <li><span>03</span><div><strong>Index</strong><p>Species counts and confidence evidence become searchable.</p></div></li>
          </ol>
        </aside>
      </section>

      {result && (
        <section className="upload-result" aria-labelledby="upload-result-heading">
          <div className="section-heading"><div><p className="eyebrow">Analysis complete</p><h2 id="upload-result-heading">Your media is ready</h2></div><span className="ready-badge">Indexed</span></div>
          <MediaCard media={result} />
        </section>
      )}
    </main>
  );
}
