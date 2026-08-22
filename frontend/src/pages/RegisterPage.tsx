import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { StatusMessage } from "../components/StatusMessage";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [values, setValues] = useState({ email: "", firstName: "", lastName: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function field(name: keyof typeof values, value: string) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(values);
      navigate("/verify", { state: { email: values.email }, replace: true });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Registration failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="single-auth">
      <section className="auth-card auth-card--wide" aria-labelledby="register-title">
        <div><p className="eyebrow">Join the field team</p><h1 id="register-title">Create your archive account</h1></div>
        <p className="muted">All fields are required. Cognito will email a six-digit verification code.</p>
        {error && <StatusMessage tone="error">{error}</StatusMessage>}
        <form onSubmit={submit}>
          <div className="form-row">
            <label>First name<input required autoComplete="given-name" value={values.firstName} onChange={(event) => field("firstName", event.target.value)} /></label>
            <label>Last name<input required autoComplete="family-name" value={values.lastName} onChange={(event) => field("lastName", event.target.value)} /></label>
          </div>
          <label>Email<input required type="email" autoComplete="email" value={values.email} onChange={(event) => field("email", event.target.value)} /></label>
          <label>Password<input required minLength={12} type="password" autoComplete="new-password" value={values.password} onChange={(event) => field("password", event.target.value)} /></label>
          <p className="field-hint">Use 12+ characters with upper/lowercase letters, a number and a symbol.</p>
          <button className="button button--primary" type="submit" disabled={busy}>{busy ? "Creating account…" : "Create account"}</button>
        </form>
        <p className="auth-switch">Already registered? <Link to="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
