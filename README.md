# Pacific BioArchive — Prototype

Pacific BioArchive is the FIT5225 Assignment 2 prototype for an authenticated,
serverless wildlife media platform. It will support image/video upload,
checksum deduplication, thumbnail generation, ML species tagging, tag/count
queries, bulk tag editing, deletion, email notifications, and a complete web UI.

## Current branch

`stage-0-baseline` preserves the supplied ML assets and test images before they
are refactored. The original script is intentionally retained under
`legacy/PacificBioArchive/`; known limitations are documented in
`docs/stages/STAGE_0_REPORT.md`.

## Repository safety

- This repository is the **Prototype** repository only.
- Model weights are tracked with Git LFS.
- Secrets, `.env` files, build output, and IDE metadata are ignored.
- AWS deployment results will only be reported after they are actually tested.

See `docs/MASTER_PLAN.md` for the complete implementation sequence.

