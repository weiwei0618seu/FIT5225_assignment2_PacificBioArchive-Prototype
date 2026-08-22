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

## Upload workflow

The upload page validates supported file type and the 10 MiB image / 50 MiB
video limits before it calculates SHA-256 in the browser. It then reserves the
checksum through the authenticated API, PUTs the file directly to the private
S3 presigned URL with every required signed header, and polls the media record
until it is `READY` or `FAILED`. The result view shows the private thumbnail or
video marker, species counts, automatic/manual tags, model version and a
short-lived link to the original.

## Query workflows

The search workspace provides all four assignment query paths:

- one species/tag, including manual tag presence;
- up to 20 minimum-count rows combined with strict logical AND;
- thumbnail URL/key to a fresh original URL;
- a temporary JPG/PNG/WebP whose detected species are used to find matches.

Temporary query images use their own short-lived signed upload flow. They are
never inserted into media/dedup records and the ML Lambda deletes the object in
`finally` on success or failure.

## Management and notifications

The management workspace can search and select ready media or accept stable
file IDs/assignment URLs directly. It supports owner-authorized bulk add/remove
of manual tags, complete deletion of originals/thumbnails/metadata/dedup state,
and per-item outcomes. Permanent deletion requires an explicit confirmation.

Notification watches use the verified Cognito email claim and 1–20 normalized
tags. `PENDING` is shown honestly until the recipient confirms the AWS SNS
email. Removing the external SNS subscription also requires confirmation.

Feature-specific pages and their tests are documented by the cumulative
Stage 5 reports in `docs/stages/`.
