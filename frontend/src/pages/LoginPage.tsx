import { type FormEvent, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { StatusMessage } from "../components/StatusMessage";

export function LoginPage() {
  const { user, login, loginGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (user) return <Navigate to="/" replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      const destination = (location.state as { from?: string } | null)?.from || "/";
      navigate(destination, { replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sign in failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function google() {
    setBusy(true);
    setError("");
    try {
      await loginGoogle();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Google sign in failed.");
      setBusy(false);
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-story">
        <p className="eyebrow">Cloud wildlife intelligence</p>
        <h1>Turn field media into searchable evidence.</h1>
        <p>
          Securely upload camera-trap images and videos, identify native wildlife,
          and find the records that matter in seconds.
        </p>
        <ul className="feature-list">
          <li>Private AWS storage</li>
          <li>Automated species detection</li>
          <li>Exact tag and count search</li>
        </ul>
      </section>
      <section className="auth-card" aria-labelledby="login-title">
        <div>
          <p className="eyebrow">Welcome back</p>
          <h2 id="login-title">Sign in to your archive</h2>
        </div>
        {error && <StatusMessage tone="error">{error}</StatusMessage>}
        <form onSubmit={submit}>
          <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button className="button button--primary" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="divider"><span>or</span></div>
        <button className="button button--google" type="button" onClick={google} disabled={busy}>
          <span aria-hidden="true">G</span> Continue with Google
        </button>
        <p className="auth-switch">New to the archive? <Link to="/register">Create an account</Link></p>
      </section>
    </main>
  );
}
