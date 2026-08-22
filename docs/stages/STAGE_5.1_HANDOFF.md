# Stage 5.1 Handoff — React authentication experience

## What this stage owns

This stage owns the SPA foundation and authentication user journey: public
configuration validation, Amplify/Cognito integration, registration, email
verification, native and Google sign-in, session restoration, protected routes,
logout, responsive styling and authentication component tests.

## Main files

- `frontend/src/auth/authClient.ts` — Cognito and Google federation adapter.
- `frontend/src/auth/AuthProvider.tsx` — restored session and auth state.
- `frontend/src/App.tsx` — public/protected routing boundary.
- `frontend/src/pages/` — sign-in, registration, verification, callback and
  initial dashboard pages.
- `frontend/src/styles.css` — responsive visual system.
- `frontend/src/App.test.tsx` and `config.test.ts` — behavior/config evidence.
- `frontend/README.md` — safe local setup.

## Verification

Run from `frontend/`:

```powershell
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
```

Expected current automated result: 7 frontend tests. Then run the cumulative
backend suite and lint `infrastructure/auth-and-iam.json`.

## Demo/review questions

- Why are Google credentials absent from the React build?
- How does Cognito's authorization-code flow protect a browser client?
- Why does the app restore a user through Amplify rather than storing tokens?
- Which registration inputs become Cognito standard attributes?
- How does the protected route behave during session loading and expiry?
- Which exact callback/logout URLs must match on Cognito and Google?

## Live steps requiring a student

During the deployment stage, provide the Google OAuth values without committing
or displaying them, confirm one Cognito verification email, and complete both
native and Google sign-in demonstrations. Do not place passwords, codes, tokens
or OAuth secrets in files, screenshots, terminal output or chat.
