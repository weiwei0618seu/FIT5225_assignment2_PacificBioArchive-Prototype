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
