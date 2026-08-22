# Pacific BioArchive — Prototype

Pacific BioArchive is the FIT5225 Assignment 2 prototype for an authenticated,
serverless wildlife media platform. It will support image/video upload,
checksum deduplication, thumbnail generation, ML species tagging, tag/count
queries, bulk tag editing, deletion, email notifications, and a complete web UI.

## Cumulative stage branches

Every `stage-X.Y-*` branch contains the complete passing project state through
that stage. `stage-0-baseline` preserves the supplied assets; later branches add
the reusable ML/media/domain/AWS/API layers in the order documented by
`docs/MASTER_PLAN.md`. The original script remains under
`legacy/PacificBioArchive/` for traceability.

## Repository safety

- This repository is the **Prototype** repository only.
- Model weights are tracked with Git LFS.
- Secrets, `.env` files, build output, and IDE metadata are ignored.
- AWS deployment results will only be reported after they are actually tested.

See `docs/MASTER_PLAN.md` for the complete implementation sequence.

## Frontend development

The React/TypeScript SPA lives in `frontend/`. Copy the public deployment
identifiers from `.env.example` into an ignored `frontend/.env.local`, then:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm run test:run
pnpm run dev
```

The SPA supports Cognito email/password registration, email verification,
native sign-in, Google federation through Cognito's authorization-code flow,
session restoration, protected routes and logout. Feature routes are added
cumulatively by the Stage 5 branches.
