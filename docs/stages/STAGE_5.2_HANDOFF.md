# Stage 5.2 Handoff — Upload and analysis results

## What this stage owns

This stage owns the typed browser API boundary, checksum-first upload workflow,
direct presigned S3 PUT with progress, bounded processing poll and the reusable
media result card.

## Main files

- `frontend/src/api/client.ts` — authenticated JSON requests and signed PUT.
- `frontend/src/api/types.ts` — REST media/upload response contract.
- `frontend/src/upload/uploadWorkflow.ts` — validation, hashing, reservation,
  upload and terminal-state polling.
- `frontend/src/pages/UploadPage.tsx` — complete user journey and status states.
- `frontend/src/components/MediaCard.tsx` — reusable READY result presentation.
- `frontend/src/pages/UploadPage.test.tsx` — core workflow UI evidence.

## Verification

Run all frontend checks:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
```

Expected cumulative frontend result at handoff: 10 tests.

## Demo/review questions

- Why is SHA-256 calculated before requesting a presigned URL?
- Which signed headers must the browser preserve on the S3 PUT?
- How are exact duplicate bytes distinguished from a failed upload?
- Why is processing polled after S3 reports a successful PUT?
- What ends polling, and how is a slow operation bounded?
- Why are S3 object keys never displayed or stored as public URLs?
- How do image and video results differ?

## Live checks for Stage 6

Test a supported image, supported short video, exact duplicate, unsupported
type, oversized file, tampered checksum and forced processing failure. Confirm
the browser never receives AWS credentials, every media URL is signed, bucket
access is private and S3/API CORS permits only the deployed SPA origins and
required methods/headers.
