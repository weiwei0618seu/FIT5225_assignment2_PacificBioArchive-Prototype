# Pacific BioArchive web application

This React 19, TypeScript and Vite single-page application is the authenticated
web client for Pacific BioArchive.

## Local configuration

Copy the `VITE_*` values from the repository `.env.example` into an ignored
`frontend/.env.local`. These are public deployment identifiers and URLs; never
put a Google client secret, AWS credential or token in a `VITE_*` variable.

The local OAuth callback and logout URLs should normally be
`http://localhost:5173/auth/callback` and `http://localhost:5173/login`, and
must exactly match the Cognito app-client configuration.

## Commands

```powershell
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
pnpm run dev
```

The frontend package is intentionally separate from the Python backend. The
committed `pnpm-lock.yaml` provides deterministic installs.

## Authentication behavior

- Registration collects email, first name, last name and password.
- Cognito sends and verifies the confirmation code.
- Native and Google users enter the same protected application shell.
- Google login uses Cognito federation with authorization code flow and PKCE.
- A restored Cognito session survives page reloads; sign-out clears it.
- API calls obtain the current ID token at request time instead of persisting
  tokens in application storage.

Feature-specific pages and their tests are documented by the cumulative
Stage 5 reports in `docs/stages/`.
