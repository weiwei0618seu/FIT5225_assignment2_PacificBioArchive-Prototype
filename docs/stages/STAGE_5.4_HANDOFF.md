# Stage 5.4 Handoff — Media management and notifications

## What this stage owns

This stage owns media selection/identifier parsing, bulk manual-tag mutation,
confirmed full deletion, per-item outcomes and the complete SNS tag-watch UI.

## Main files

- `frontend/src/pages/ManagePage.tsx` — management and notification workflows.
- `frontend/src/components/ConfirmPanel.tsx` — accessible destructive-action
  confirmation.
- `frontend/src/api/client.ts` — tag/delete/subscription requests.
- `frontend/src/pages/ManagePage.test.tsx` — confirmation, mutation and pending
  state evidence.

## Verification

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
```

Expected cumulative frontend result: 17 tests.

## Demo/review questions

- What is the difference between automatic and manual tags?
- Who is allowed to edit/delete a ready record found through public search?
- Which four durable objects/states does a complete delete remove?
- Why is repeated deletion not a server error?
- Why does the notification form have no email field?
- What does HTTP 202/PENDING mean for an SNS subscription?
- Do manual tag additions trigger a watched-tag notification?
- Which actions require explicit confirmation and why?

## Live checks for Stage 6

Prove owner tag add/remove, non-owner `403`, automatic and manual watched-tag
notification behavior, pending-to-confirmed SNS status, full deletion, repeated
deletion and confirmed unsubscribe. Use only disposable demo records for the
destructive checks.
