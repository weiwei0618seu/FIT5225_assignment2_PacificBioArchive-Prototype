import { type FormEvent, useEffect, useMemo, useState } from "react";

import {
  deleteMedia,
  deleteNotificationSubscription,
  editMediaTags,
  getNotificationSubscription,
  querySpecies,
  setNotificationSubscription,
} from "../api/client";
import type { DeleteResponse, MediaRecord, Subscription } from "../api/types";
import { ConfirmPanel } from "../components/ConfirmPanel";
import { MediaCard } from "../components/MediaCard";
import { StatusMessage } from "../components/StatusMessage";

function splitValues(value: string): string[] {
  return [...new Set(value.split(/[\n,]+/).map((item) => item.trim()).filter(Boolean))];
}

function splitIdentifiers(value: string): { fileIds: string[]; urls: string[] } {
  const fileIds: string[] = [];
  const urls: string[] = [];
  for (const item of splitValues(value)) {
    (item.includes("://") || item.includes("/") ? urls : fileIds).push(item);
  }
  return { fileIds, urls };
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The management action failed.";
}

export function ManagePage() {
  const [searchTag, setSearchTag] = useState("");
  const [media, setMedia] = useState<MediaRecord[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [identifiers, setIdentifiers] = useState("");
  const [tags, setTags] = useState("");
  const [operation, setOperation] = useState<0 | 1>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteResult, setDeleteResult] = useState<DeleteResponse | null>(null);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [watchTags, setWatchTags] = useState("");
  const [notificationBusy, setNotificationBusy] = useState(false);
  const [notificationError, setNotificationError] = useState("");
  const [notificationMessage, setNotificationMessage] = useState("");
  const [confirmUnsubscribe, setConfirmUnsubscribe] = useState(false);

  useEffect(() => {
    void getNotificationSubscription()
      .then(({ subscription: current }) => {
        setSubscription(current);
        setWatchTags(current?.tags.join(", ") || "");
      })
      .catch((caught) => setNotificationError(errorMessage(caught)));
  }, []);

  const actionIdentifiers = useMemo(() => {
    const parsed = splitIdentifiers(identifiers);
    return { ...parsed, fileIds: [...new Set([...selected, ...parsed.fileIds])] };
  }, [identifiers, selected]);
  const itemCount = actionIdentifiers.fileIds.length + actionIdentifiers.urls.length;

  async function runMediaAction(action: () => Promise<void>) {
    setBusy(true); setError(""); setSuccess(""); setDeleteResult(null);
    try { await action(); } catch (caught) { setError(errorMessage(caught)); } finally { setBusy(false); }
  }

  function findMedia(event: FormEvent) {
    event.preventDefault();
    void runMediaAction(async () => {
      if (!searchTag.trim()) throw new Error("Enter a species or tag to find media.");
      const response = await querySpecies(searchTag.trim());
      setMedia(response.media);
      setSelected(new Set());
      if (!response.media.length) setSuccess("No ready media matched that tag.");
    });
  }

  function applyTags(event: FormEvent) {
    event.preventDefault();
    void runMediaAction(async () => {
      if (!itemCount) throw new Error("Select media or paste at least one file ID/URL.");
      if (itemCount > 25) throw new Error("At most 25 media items can be changed at once.");
      const normalizedTags = splitValues(tags);
      if (!normalizedTags.length) throw new Error("Enter at least one tag.");
      const result = await editMediaTags(actionIdentifiers, normalizedTags, operation);
      const changed = Object.values(result.changed_tags).reduce((total, values) => total + values.length, 0);
      setSuccess(`${operation === 1 ? "Added" : "Removed"} ${changed} tag ${changed === 1 ? "change" : "changes"} across ${result.media.length} media ${result.media.length === 1 ? "record" : "records"}.`);
      setMedia((current) => current.map((item) => result.media.find((updated) => updated.file_id === item.file_id) || item));
    });
  }

  async function confirmMediaDelete() {
    await runMediaAction(async () => {
      const result = await deleteMedia(actionIdentifiers);
      setDeleteResult(result);
      const removed = result.outcomes.filter((item) => item.deleted).map((item) => item.file_id);
      setMedia((current) => current.filter((item) => !removed.includes(item.file_id)));
      setSelected(new Set());
      setIdentifiers("");
      setSuccess(result.complete ? "Deletion completed for every requested item." : "Deletion was incomplete; review the outcomes and retry safely.");
    });
    setConfirmDelete(false);
  }

  function saveSubscription(event: FormEvent) {
    event.preventDefault();
    setNotificationBusy(true); setNotificationError(""); setNotificationMessage("");
    const normalized = splitValues(watchTags);
    if (!normalized.length) { setNotificationError("Enter at least one notification tag."); setNotificationBusy(false); return; }
    void setNotificationSubscription(normalized)
      .then((current) => {
        setSubscription(current);
        setNotificationMessage(current.status === "PENDING" ? "Check your verified Cognito email and confirm the AWS SNS subscription." : "Notification filters are active.");
      })
      .catch((caught) => setNotificationError(errorMessage(caught)))
      .finally(() => setNotificationBusy(false));
  }

  async function confirmSubscriptionDelete() {
    setNotificationBusy(true); setNotificationError(""); setNotificationMessage("");
    try {
      const deleted = await deleteNotificationSubscription();
      setSubscription(null); setWatchTags("");
      setNotificationMessage(deleted ? "Email notification subscription removed." : "No active subscription was present.");
    } catch (caught) { setNotificationError(errorMessage(caught)); }
    finally { setNotificationBusy(false); setConfirmUnsubscribe(false); }
  }

  return (
    <main className="page manage-page">
      <div className="page-heading"><div><p className="eyebrow">Owner controls</p><h1>Manage your archive</h1></div><span className="secure-pill">Bulk limit 25</span></div>

      <section className="management-section">
        <div className="section-heading"><div><p className="eyebrow">Step 1</p><h2>Find and select media</h2></div><p>Only an uploader can change or delete their media.</p></div>
        <form className="inline-search" onSubmit={findMedia}><label><span>Species or tag</span><input value={searchTag} onChange={(event) => setSearchTag(event.target.value)} placeholder="e.g. dingo" /></label><button className="button button--primary" disabled={busy}>Find media</button></form>
        {media.length > 0 && <div className="management-results">{media.map((item) => <MediaCard key={item.file_id} media={item} compact selectable selected={selected.has(item.file_id)} onSelectedChange={(checked) => setSelected((current) => { const next = new Set(current); if (checked) next.add(item.file_id); else next.delete(item.file_id); return next; })} />)}</div>}
      </section>

      <section className="management-section">
        <div className="section-heading"><div><p className="eyebrow">Step 2</p><h2>Edit or remove</h2></div><span className="selection-count">{itemCount} selected</span></div>
        <label className="textarea-field"><span>Additional file IDs or assignment URLs</span><textarea value={identifiers} onChange={(event) => setIdentifiers(event.target.value)} rows={3} placeholder="One file ID or original/thumbnail URL per line" /><small>Selected cards are added automatically. IDs/URLs are deduplicated.</small></label>
        <form className="tag-editor" onSubmit={applyTags}>
          <label><span>Manual tags</span><input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="night, reviewed" /></label>
          <label><span>Operation</span><select value={operation} onChange={(event) => setOperation(Number(event.target.value) as 0 | 1)}><option value="1">Add tags</option><option value="0">Remove tags</option></select></label>
          <button className="button button--primary" disabled={busy}>Apply tags</button>
        </form>
        <div className="danger-zone"><div><strong>Delete selected media</strong><p>Removes the original/video, thumbnail, metadata and checksum reservation.</p></div><button className="button button--danger" type="button" disabled={busy || !itemCount} onClick={() => setConfirmDelete(true)}>Delete media…</button></div>
        {error && <StatusMessage tone="error">{error}</StatusMessage>}
        {success && <StatusMessage tone="success">{success}</StatusMessage>}
        {deleteResult && <ul className="outcome-list">{deleteResult.outcomes.map((item) => <li key={item.identifier}><code>{item.file_id || item.identifier}</code><span>{item.deleted ? "Deleted" : item.already_absent ? "Already absent" : item.error_code || "Not deleted"}</span></li>)}</ul>}
      </section>

      <section className="management-section notification-section">
        <div className="section-heading"><div><p className="eyebrow">Email watch</p><h2>Tag notifications</h2></div>{subscription && <span className={`subscription-badge subscription-badge--${subscription.status.toLowerCase()}`}>{subscription.status}</span>}</div>
        <p className="section-copy">AWS SNS uses the verified email from your Cognito token. The browser cannot provide or replace it.</p>
        <form className="subscription-form" onSubmit={saveSubscription}><label><span>Watched tags</span><input value={watchTags} onChange={(event) => setWatchTags(event.target.value)} placeholder="dingo, wombat" /></label><button className="button button--primary" disabled={notificationBusy}>{subscription ? "Update watch" : "Start watching"}</button></form>
        {subscription?.status === "PENDING" && <StatusMessage tone="info">Pending confirmation for {subscription.email}. Open the AWS SNS email and select “Confirm subscription”; then reload this page to refresh status.</StatusMessage>}
        {notificationError && <StatusMessage tone="error">{notificationError}</StatusMessage>}
        {notificationMessage && <StatusMessage tone="success">{notificationMessage}</StatusMessage>}
        {subscription && <button className="text-danger" type="button" onClick={() => setConfirmUnsubscribe(true)}>Remove email subscription…</button>}
      </section>

      {confirmDelete && <ConfirmPanel title={`Permanently delete ${itemCount} ${itemCount === 1 ? "item" : "items"}?`} detail="This removes private S3 objects, metadata and duplicate reservations. It cannot be undone from this application." confirmLabel="Delete permanently" busy={busy} onCancel={() => setConfirmDelete(false)} onConfirm={() => void confirmMediaDelete()} />}
      {confirmUnsubscribe && <ConfirmPanel title="Remove email subscription?" detail="AWS SNS will stop sending notifications for every watched tag." confirmLabel="Remove subscription" busy={notificationBusy} onCancel={() => setConfirmUnsubscribe(false)} onConfirm={() => void confirmSubscriptionDelete()} />}
    </main>
  );
}
