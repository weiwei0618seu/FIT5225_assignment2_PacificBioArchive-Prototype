export function LoadingScreen() {
  return (
    <main className="center-screen" aria-busy="true">
      <div className="spinner" aria-hidden="true" />
      <p>Restoring your secure session…</p>
    </main>
  );
}
