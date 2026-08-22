# Stage 5.2 Report — Upload and analysis results

## Goal and boundary

Expose the complete authenticated upload journey through the existing REST
contract: local validation and checksum, duplicate-aware reservation, direct S3
upload, asynchronous status polling and usable READY/FAILED result states. No
live AWS or real-model success is claimed in this UI stage.

## Completed behavior

- Added a typed API client that obtains the current Cognito ID token at request
  time, sends `Authorization: Bearer`, disables response caching and converts
  stable backend errors into structured `ApiError` objects.
- Client validation matches the backend content-type allowlist and 10 MiB image
  / 50 MiB video limits.
- SHA-256 is calculated locally before `POST /uploads/init`; exact duplicates
  receive specific, recoverable guidance instead of uploading bytes.
- S3 PUT uses `XMLHttpRequest` so the UI can display byte progress, and copies
  every signed header from the upload ticket rather than reconstructing it.
- Polls `GET /media/{file_id}` at a bounded two-second interval, terminates on
  `READY` or `FAILED`, and stops after five minutes with a file-ID recovery
  message.
- Provides distinct hashing, duplicate-check, uploading and ML-processing
  progress states, plus unsupported, empty, oversized, storage, duplicate,
  processing-failure and timeout feedback.
- Shows image thumbnails or a video result marker, species counts, all tags,
  model version, video sample count and a new short-lived original link.
- Added protected `/upload` navigation and a dashboard call to action.
- Extended the responsive design down to a single-column 320 px layout and
  retained accessible labels, live status and reduced-motion behavior.

## Created files

- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/upload/uploadWorkflow.ts`
- `frontend/src/pages/UploadPage.tsx`
- `frontend/src/pages/UploadPage.test.tsx`
- `frontend/src/components/MediaCard.tsx`
- `docs/stages/STAGE_5.2_REPORT.md`
- `docs/stages/STAGE_5.2_HANDOFF.md`

## Modified files

- `frontend/src/App.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/pages/DashboardPage.tsx`
- `frontend/src/styles.css`
- `frontend/README.md`
- `docs/GENAI_USAGE.md`

## Verification

```powershell
cd frontend
pnpm run typecheck
# passed

pnpm run test:run
# 3 files, 10 tests passed

pnpm run build
# 639 modules transformed; production build passed

pnpm run lint
# exit 0, no findings
```

The three upload component tests prove successful result rendering, rejection
of unsupported input before the API and explicit checksum-duplicate feedback.

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

None. The signed PUT and polling logic are contract-tested with mocked frontend
workflow boundaries. Live S3 upload requires the Stage 6 stack, including exact
S3 CORS headers and API Gateway CORS configuration.

## Known risks/later work

- Browser SHA-256 currently reads the selected file into memory; the enforced
  50 MiB maximum bounds this, but a streaming hash would improve large-file
  ergonomics outside the assignment scope.
- Presigned GET URLs expire after 15 minutes; every later query refreshes them
  instead of persisting them.
- The processing Lambda's real supplied detector/classifier smoke test remains
  unproven until the pinned Linux container is built and executed in Stage 6.2.
