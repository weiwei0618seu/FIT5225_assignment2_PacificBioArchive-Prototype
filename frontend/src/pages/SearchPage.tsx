import { type FormEvent, useState } from "react";

import {
  lookupThumbnail,
  queryRequirements,
  querySpecies,
} from "../api/client";
import type { QueryResponse, TemporaryQueryResponse, ThumbnailLookup } from "../api/types";
import { MediaResults } from "../components/MediaResults";
import { StatusMessage } from "../components/StatusMessage";
import {
  ACCEPTED_QUERY_TYPES,
  runTemporaryQuery,
  validateTemporaryQueryFile,
  type TemporaryQueryProgress,
} from "../queries/temporaryQueryWorkflow";

type Mode = "requirements" | "species" | "thumbnail" | "file";
type RequirementRow = { id: number; tag: string; count: string };

const MODES: { id: Mode; label: string; detail: string }[] = [
  { id: "requirements", label: "Counts", detail: "Strict AND" },
  { id: "species", label: "Species", detail: "One tag" },
  { id: "thumbnail", label: "Thumbnail", detail: "Find original" },
  { id: "file", label: "Image", detail: "Visual query" },
];

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The query could not be completed.";
}

export function SearchPage() {
  const [mode, setMode] = useState<Mode>("requirements");
  const [rows, setRows] = useState<RequirementRow[]>([{ id: 1, tag: "", count: "1" }]);
  const [nextRow, setNextRow] = useState(2);
  const [species, setSpecies] = useState("");
  const [thumbnail, setThumbnail] = useState("");
  const [queryFile, setQueryFile] = useState<File | null>(null);
  const [queryProgress, setQueryProgress] = useState<TemporaryQueryProgress | null>(null);
  const [results, setResults] = useState<QueryResponse | null>(null);
  const [tempResult, setTempResult] = useState<TemporaryQueryResponse | null>(null);
  const [thumbnailResult, setThumbnailResult] = useState<ThumbnailLookup | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function resetOutput() {
    setResults(null);
    setTempResult(null);
    setThumbnailResult(null);
    setError("");
  }

  function chooseMode(selected: Mode) {
    setMode(selected);
    resetOutput();
  }

  async function run(action: () => Promise<void>) {
    setBusy(true);
    resetOutput();
    try {
      await action();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
      setQueryProgress(null);
    }
  }

  function submitRequirements(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      const requirements: Record<string, number> = {};
      for (const row of rows) {
        const tag = row.tag.trim().toLowerCase();
        if (!tag) throw new Error("Every requirement needs a species or tag.");
        const count = Number(row.count);
        if (!Number.isInteger(count) || count < 1) throw new Error("Every minimum count must be at least one.");
        requirements[tag] = Math.max(requirements[tag] || 0, count);
      }
      setResults(await queryRequirements(requirements));
    });
  }

  function submitSpecies(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      if (!species.trim()) throw new Error("Enter a species or tag.");
      setResults(await querySpecies(species.trim()));
    });
  }

  function submitThumbnail(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      if (!thumbnail.trim()) throw new Error("Paste a thumbnail URL or key.");
      setThumbnailResult(await lookupThumbnail(thumbnail.trim()));
    });
  }

  function submitFile(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      if (!queryFile) throw new Error("Choose a query image.");
      const response = await runTemporaryQuery(queryFile, setQueryProgress);
      setTempResult(response);
      setResults(response);
    });
  }

  return (
    <main className="page search-page">
      <div className="page-heading"><div><p className="eyebrow">Precise discovery</p><h1>Search the archive</h1></div><span className="secure-pill">Logical AND · private URLs</span></div>
      <div className="query-tabs" role="tablist" aria-label="Query mode">
        {MODES.map((item) => (
          <button key={item.id} role="tab" aria-selected={mode === item.id} type="button" onClick={() => chooseMode(item.id)}>
            <strong>{item.label}</strong><small>{item.detail}</small>
          </button>
        ))}
      </div>

      <section className="query-panel" role="tabpanel">
        {mode === "requirements" && (
          <form onSubmit={submitRequirements}>
            <div className="query-intro"><div><p className="eyebrow">Minimum counts</p><h2>Match every requirement</h2></div><p>A record must meet all rows. Manual tags count as one.</p></div>
            <div className="requirement-list">
              {rows.map((row, index) => (
                <div className="requirement-row" key={row.id}>
                  <label><span>Species or tag {index + 1}</span><input value={row.tag} maxLength={50} onChange={(event) => setRows((current) => current.map((item) => item.id === row.id ? { ...item, tag: event.target.value } : item))} placeholder="e.g. dingo" /></label>
                  <label><span>Minimum</span><input type="number" min="1" max="999" value={row.count} onChange={(event) => setRows((current) => current.map((item) => item.id === row.id ? { ...item, count: event.target.value } : item))} /></label>
                  <button className="icon-button" type="button" aria-label={`Remove requirement ${index + 1}`} disabled={rows.length === 1} onClick={() => setRows((current) => current.filter((item) => item.id !== row.id))}>×</button>
                </div>
              ))}
            </div>
            <div className="query-actions"><button className="button button--quiet" type="button" disabled={rows.length >= 20} onClick={() => { setRows((current) => [...current, { id: nextRow, tag: "", count: "1" }]); setNextRow((value) => value + 1); }}>+ Add requirement</button><button className="button button--primary" disabled={busy}>Search counts</button></div>
          </form>
        )}

        {mode === "species" && (
          <form onSubmit={submitSpecies}>
            <div className="query-intro"><div><p className="eyebrow">Species query</p><h2>Find one tag</h2></div><p>Matches automatic detections or manually added tags.</p></div>
            <label className="query-field"><span>Species or tag</span><input value={species} maxLength={50} onChange={(event) => setSpecies(event.target.value)} placeholder="e.g. wombat" /></label>
            <button className="button button--primary" disabled={busy}>Search species</button>
          </form>
        )}

        {mode === "thumbnail" && (
          <form onSubmit={submitThumbnail}>
            <div className="query-intro"><div><p className="eyebrow">Reverse lookup</p><h2>Recover an original</h2></div><p>Paste a Pacific BioArchive thumbnail URL or its stable key.</p></div>
            <label className="query-field"><span>Thumbnail URL or key</span><input type="text" value={thumbnail} onChange={(event) => setThumbnail(event.target.value)} placeholder="https://…/thumbnails/file.jpg" /></label>
            <button className="button button--primary" disabled={busy}>Find original</button>
          </form>
        )}

        {mode === "file" && (
          <form onSubmit={submitFile}>
            <div className="query-intro"><div><p className="eyebrow">Temporary inference</p><h2>Search with an image</h2></div><p>The query image is deleted after inference, including on processing failure.</p></div>
            <label className="query-file"><input type="file" accept={ACCEPTED_QUERY_TYPES.join(",")} onChange={(event) => { const file = event.target.files?.[0] || null; resetOutput(); if (!file) return setQueryFile(null); try { validateTemporaryQueryFile(file); setQueryFile(file); } catch (caught) { setQueryFile(null); setError(errorMessage(caught)); event.target.value = ""; } }} /><span>{queryFile ? queryFile.name : "Choose JPG, PNG or WebP"}</span><small>Maximum 10 MiB · never added to the archive</small></label>
            {queryProgress && <div className="compact-progress" role="status"><span>{queryProgress.phase === "hashing" ? "Hashing image" : queryProgress.phase === "uploading" ? `Uploading ${queryProgress.percent || 0}%` : "Detecting species and finding matches"}</span><progress max="100" value={queryProgress.phase === "uploading" ? queryProgress.percent || 0 : undefined} /></div>}
            <button className="button button--primary" disabled={busy || !queryFile}>{busy ? "Analysing…" : "Analyse and search"}</button>
          </form>
        )}
        {error && <StatusMessage tone="error">{error}</StatusMessage>}
      </section>

      {thumbnailResult && <section className="lookup-result"><div><p className="eyebrow">Original located</p><h2>File {thumbnailResult.file_id}</h2></div><a className="button button--primary" href={thumbnailResult.original_url} target="_blank" rel="noreferrer">Open original</a></section>}
      {tempResult && <section className="detected-summary"><div><p className="eyebrow">Query image detected</p><h2>{Object.keys(tempResult.detected_species_counts).join(", ") || "No species"}</h2></div><dl>{Object.entries(tempResult.detected_species_counts).map(([tag, count]) => <div key={tag}><dt>{tag}</dt><dd>{count}</dd></div>)}</dl><small>Model {tempResult.model_version || "not reported"}</small></section>}
      {results && <MediaResults media={results.media} total={results.total} truncated={results.truncated} />}
    </main>
  );
}
