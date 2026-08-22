import { Link } from "react-router-dom";

export function DashboardPage() {
  return (
    <main className="page dashboard">
      <div className="page-heading">
        <div><p className="eyebrow">Protected workspace</p><h1>Archive overview</h1></div>
        <span className="secure-pill">Secure session</span>
      </div>
      <section className="hero-panel">
        <div><p className="eyebrow">Pacific BioArchive</p><h2>Your wildlife evidence, organised by intelligence.</h2><p>Private checksum-first media ingest and wildlife analysis are ready.</p><Link className="button button--primary hero-action" to="/upload">Upload media</Link></div>
        <div className="signal" aria-label="System ready"><span /><span /><span /></div>
      </section>
      <section className="metric-grid" aria-label="Workspace capabilities">
        <article><span>01</span><h3>Private ingest</h3><p>Checksum-first uploads keep duplicate bytes out of storage.</p></article>
        <article><span>02</span><h3>Wildlife inference</h3><p>Images and exact one-frame-per-second video samples become species tags.</p></article>
        <article><span>03</span><h3>Precise discovery</h3><p>Find records using strict multi-species minimum counts.</p></article>
      </section>
    </main>
  );
}
