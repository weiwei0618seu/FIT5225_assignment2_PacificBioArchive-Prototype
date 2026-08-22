# Stage 5.3 Report — Complete query workspace

## Goal and boundary

Expose all rubric query modes through one protected, responsive workspace:
single species/tag, strict multi-tag minimum-count AND, thumbnail-to-original
lookup, and temporary-image inference. This stage consumes the tested REST
contract and does not claim live ML/AWS success.

## Completed behavior

- Extended the typed API client for tags, species, thumbnail and temporary-file
  endpoints without persisting Cognito tokens or signed URLs.
- Minimum-count search supports 1–20 dynamic rows, validates non-empty tags and
  positive integers, normalizes tag case and combines duplicate tag rows using
  the largest requested minimum.
- Single-tag search documents and displays both automatic species detections
  and manual-tag matches.
- Thumbnail lookup accepts the assignment's signed URL form or a stable
  thumbnail key and returns a new private original link.
- Temporary query accepts JPG, PNG or WebP up to 10 MiB, calculates SHA-256,
  requests a user-scoped signed upload, preserves all signed S3 headers, invokes
  the separate ML route and displays the inferred species counts/model version.
- The UI states explicitly that a temporary image is not archived. Backend
  `finally` cleanup remains the authoritative success/failure deletion control.
- Reusable query results show total/truncated state, image thumbnails, video
  markers, counts/tags and short-lived original URLs; honest empty results do
  not imply an error.
- Added accessible tab semantics, dynamic field labels, loading/error states and
  responsive two-column-to-single-column result layout.

## Created files

- `frontend/src/queries/temporaryQueryWorkflow.ts`
- `frontend/src/components/MediaResults.tsx`
- `frontend/src/pages/SearchPage.tsx`
- `frontend/src/pages/SearchPage.test.tsx`
- `docs/stages/STAGE_5.3_REPORT.md`
- `docs/stages/STAGE_5.3_HANDOFF.md`

## Modified files

- `frontend/src/api/client.ts`
- `frontend/src/api/types.ts`
- `frontend/src/components/MediaCard.tsx`
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
# 4 files, 14 tests passed

pnpm run build
# 642 modules transformed; production build passed

pnpm run lint
# exit 0, no findings
```

Four query component tests prove normalized logical-AND request construction,
an honest empty species result, thumbnail reverse lookup and a temporary-image
result with detected counts.

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

None. Live temporary-image proof depends on the Stage 6 ML container and its
real supplied-model smoke test. No query object or AWS resource was created in
this stage.

## Known risks/later work

- Query results currently request at most the API default 50 items and clearly
  show truncation; cursor pagination is not yet exposed because the backend
  contract does not yet return a continuation token.
- Signed query-result URLs expire in 15 minutes and must be refreshed by
  repeating the query.
- Stage 6 must prove temporary-object removal with S3 evidence on both a normal
  result and a forced inference/checksum error.
