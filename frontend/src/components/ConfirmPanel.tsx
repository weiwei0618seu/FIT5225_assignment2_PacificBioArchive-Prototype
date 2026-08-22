type Props = {
  title: string;
  detail: string;
  confirmLabel: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmPanel({ title, detail, confirmLabel, busy = false, onConfirm, onCancel }: Props) {
  return (
    <div className="confirm-backdrop" role="presentation">
      <section className="confirm-panel" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-detail">
        <p className="eyebrow">Confirmation required</p>
        <h2 id="confirm-title">{title}</h2>
        <p id="confirm-detail">{detail}</p>
        <div><button className="button button--quiet" type="button" onClick={onCancel} disabled={busy}>Cancel</button><button className="button button--danger" type="button" onClick={onConfirm} disabled={busy}>{busy ? "Working…" : confirmLabel}</button></div>
      </section>
    </div>
  );
}
