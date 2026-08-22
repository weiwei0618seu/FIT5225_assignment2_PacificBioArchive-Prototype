# Stage 5.4 Report — Media management and notifications

## Goal and boundary

Complete the remaining end-user workflows: owner-authorized bulk manual tags,
full idempotent deletion and Cognito-email SNS tag watches. Destructive actions
must require clear in-application confirmation. This stage does not create or
remove live AWS subscriptions/media.

## Completed behavior

- Added typed client methods and response contracts for bulk tag edits,
  per-item deletion outcomes and notification get/set/delete.
- Users can search ready media by a tag and select cards, or paste stable file
  IDs and assignment-compatible original/thumbnail URLs directly.
- Selected and pasted identifiers are deduplicated and bounded to 25 items.
- Add/remove accepts up to 20 comma/newline-delimited tags and displays the
  exact number of effective tag changes; no-change operations remain honest.
- Media deletion uses an accessible modal confirmation before the request and
  explains that S3 originals/videos, thumbnails, metadata and checksum
  reservations are all affected.
- Displays `Deleted`, `Already absent` or an error code per input, supporting
  safe idempotent retry and partial-failure diagnosis.
- Notification UI never accepts an email address: the backend uses the verified
  Cognito claim. It creates/updates watched tags, reloads actual SNS status and
  distinguishes `PENDING` confirmation from `CONFIRMED` delivery.
- Pending guidance names the claimed verified email and explains the required
  SNS email-confirmation action without exposing tokens or codes.
- Removing an SNS subscription requires a separate confirmation dialog.
- Added protected `/manage` navigation plus responsive mobile layouts for card
  selection, forms, danger zones, outcomes and confirmation panels.

## Created files

- `frontend/src/components/ConfirmPanel.tsx`
- `frontend/src/pages/ManagePage.tsx`
- `frontend/src/pages/ManagePage.test.tsx`
- `docs/stages/STAGE_5.4_REPORT.md`
- `docs/stages/STAGE_5.4_HANDOFF.md`

## Modified files

- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/styles.css`
- `frontend/README.md`
- `docs/GENAI_USAGE.md`

## Verification

```powershell
cd frontend
pnpm run typecheck
# passed

pnpm run test:run
# 5 files, 17 tests passed

pnpm run build
# 644 modules transformed; production build passed

pnpm run lint
# exit 0, no findings
```

The three new component tests prove selected bulk tag mutation, no delete call
before confirmation plus a successful per-item outcome, and honest SNS pending
email guidance.

```powershell
uv run --project backend --extra dev pytest -q backend/tests
# 96 passed

uvx --from cfn-lint cfn-lint infrastructure/auth-and-iam.json
# exit 0, no findings

git diff --check
# exit 0
```

The credential-shape scan found no AWS access-key IDs, private-key blocks,
Google client-secret assignments or AWS secret-access-key assignments.

## AWS operations and manual blockers

None. The UI is tested at the client boundary only. A real email subscription
will remain `PENDING` until the user opens the AWS SNS email and confirms it;
this cannot be automated or claimed early.

## Known risks/later work

- Search results can contain another uploader's READY media; the backend remains
  authoritative and rejects mutation with `403 FORBIDDEN`.
- Live deletion evidence should use disposable demo media and capture the
  before/after S3/DynamoDB state without displaying signed URLs or tokens.
- SNS confirmation and Google federation require user-controlled external
  identity actions during deployment.
