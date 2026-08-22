# Stage 5.1 Report — React authentication experience

## Goal and boundary

Create a responsive React/TypeScript SPA with the complete Cognito entry flow:
native registration, required profile attributes, email verification, native
sign-in, Google federation, session restoration, protected routing and logout.
This stage uses mocked authentication in automated tests and does not claim a
live Cognito or Google login before the AWS deployment stage.

## Completed behavior

- Added a React 19, TypeScript and Vite application with deterministic pnpm
  dependency locking and separate typecheck, test, build and lint commands.
- Validates all required public deployment configuration before rendering so a
  bad build cannot silently target the wrong API or user pool.
- Configures Amplify Auth for the Cognito user pool, code-based sign-up
  verification and hosted Google login with authorization-code flow.
- Registration requires email, first name, last name and password and maps the
  profile fields to `given_name` and `family_name`.
- Added confirmation-code handling, native sign-in, Google sign-in, logout and
  readable non-secret error messages.
- Restores the current Cognito user on refresh, guards application routes and
  returns unauthenticated users to the login page.
- Added a polished responsive application shell and auth experience tested at
  desktop and 390 x 844 mobile viewports in the team's connected Chrome.
- Enabled both React Router v7 future flags; the final reload produced no
  router warnings or application errors in the new browser log entries.
- Documented local setup and prohibited secrets in `VITE_*` variables.

## Created files

- `frontend/` React application, source, tests, package metadata and lockfile.
- `frontend/README.md`
- `docs/stages/STAGE_5.1_REPORT.md`
- `docs/stages/STAGE_5.1_HANDOFF.md`

## Modified files

- `README.md`
- `docs/GENAI_USAGE.md`

## Verification

Observed results:

```powershell
cd frontend
pnpm run typecheck
# passed

pnpm run test:run
# 2 files, 7 tests passed

pnpm run build
# 635 modules transformed; production build passed

pnpm run lint
# passed with no findings
```

Chrome desktop and mobile visual checks covered layout, labels, navigation,
focusable controls and overflow. After enabling the router future flags, the
latest page reload logged only the Vite connection and React development-info
messages; the prior two warnings were not repeated.

```powershell
uv run --project backend --extra dev pytest -q backend/tests
# 96 passed

uvx --from cfn-lint cfn-lint infrastructure/auth-and-iam.json
# exit 0, no findings

git diff --check
# exit 0
```

A credential-shape scan found no AWS access-key IDs, private-key blocks, Google
client-secret assignments or AWS secret-access-key assignments.

## AWS operations and manual blockers

None. No AWS resource or paid service was used in this stage. Live native auth
requires a deployed Cognito pool and one user-controlled email confirmation.
Live Google federation additionally requires the team's OAuth client ID/secret
provided as transient `NoEcho` deployment inputs.

## Known risks/later work

- API feature pages still need to attach a fresh ID token to each request and
  handle expired sessions consistently.
- Hosted callback/logout URLs must be replaced with the final CloudFront URLs
  before deployment.
- Live evidence must test native registration, verification, logout, reload,
  invalid session rejection and Google login without exposing tokens.
