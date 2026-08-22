import { type FormEvent, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { StatusMessage } from "../components/StatusMessage";

export function VerifyPage() {
  const { verify } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const initialEmail = (location.state as { email?: string } | null)?.email || "";
  const [email, setEmail] = useState(initialEmail);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await verify(email, code);
      navigate("/login", { state: { verified: true }, replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Verification failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="single-auth">
      <section className="auth-card" aria-labelledby="verify-title">
        <div><p className="eyebrow">Check your inbox</p><h1 id="verify-title">Verify your email</h1></div>
        <p className="muted">Enter the confirmation code sent by Amazon Cognito.</p>
        {error && <StatusMessage tone="error">{error}</StatusMessage>}
        <form onSubmit={submit}>
          <label>Email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Verification code<input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" required value={code} onChange={(event) => setCode(event.target.value)} /></label>
          <button className="button button--primary" type="submit" disabled={busy}>{busy ? "Verifying…" : "Verify email"}</button>
        </form>
        <p className="auth-switch"><Link to="/login">Back to sign in</Link></p>
      </section>
    </main>
  );
}
