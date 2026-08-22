# Stage 5.3 Handoff — Complete query workspace

## What this stage owns

This stage owns all four end-user query modes, typed query responses, temporary
query upload orchestration and reusable result/empty/truncated presentation.

## Main files

- `frontend/src/pages/SearchPage.tsx` — four accessible query panels.
- `frontend/src/queries/temporaryQueryWorkflow.ts` — image validation, checksum,
  signed PUT and ML execution.
- `frontend/src/components/MediaResults.tsx` — total, truncation, empty state and
  media grid.
- `frontend/src/api/client.ts` — authenticated query routes.
- `frontend/src/pages/SearchPage.test.tsx` — request and result evidence.

## Verification

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
```

Expected cumulative frontend result: 14 tests.

## Demo/review questions

- Is a multi-row count query OR or strict AND, and where is that proven?
- How does a manual tag contribute to a minimum-count query?
- Why does a thumbnail lookup return a new URL instead of the stored URL?
- Why is the temporary query restricted to images?
- Which key prefix binds a temporary object to a Cognito subject/query ID?
- What guarantees object deletion when inference fails?
- What does an empty result mean compared with an API error?

## Live checks for Stage 6

Demonstrate a multi-species/count AND match and non-match, one manual-tag match,
thumbnail lookup, a temporary image with a result, an image with no detected
species, a foreign temp key rejection and successful S3 cleanup after both
success and forced failure.
