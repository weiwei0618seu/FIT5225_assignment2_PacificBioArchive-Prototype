# Stage 0 Handoff — Supplied ML Baseline

## What this stage owns

The immutable reference copy of the provided detector, classifier, label map,
batch script, and real test images.

## Important files

- `legacy/PacificBioArchive/batch.py`
- `legacy/PacificBioArchive/model.pt`
- `legacy/PacificBioArchive/mdv5a.pt`
- `legacy/PacificBioArchive/labels.txt`
- `tests/fixtures/images/`

## What a student must understand

1. MegaDetector locates animal bounding boxes.
2. Detected animal crops are resized and classified by the fine-tuned model.
3. The classifier has 46 ordered output classes.
4. This script currently prints predictions and must be converted into a
   reusable, lazy-loaded inference service.
5. Model paths/version/checksums must become configuration, not source edits.

## How to verify

- Confirm Git LFS reports both `.pt` files as LFS objects.
- Validate model SHA-256 values against `STAGE_0_REPORT.md`.
- Decode at least one fixture image.
- Run Python syntax compilation on `batch.py`.

## Likely demo questions

- Why use MegaDetector before species classification?
- How are multiple animals counted?
- How can a future model version be deployed without changing business code?
- Why are the weights stored with Git LFS and later copied to S3/ECR?

