# Stage 3.2 Report — Asynchronous Media Processing

## Goal and boundary

Consume private-media S3 `ObjectCreated` events, verify that the uploaded bytes
match the reserved ticket, run the existing image/video pipelines, and persist
an idempotent terminal state. Notifications, REST routing, and infrastructure
wiring remain later stages.

## Completed behavior

- Strictly parses URL-encoded S3 records and accepts only `aws:s3`
  `ObjectCreated` events from the configured bucket.
- Resolves `originals/<file_id>/<filename>` to its record and requires an exact
  durable object-key match.
- Treats a replay for `READY` media as success without downloading or running
  ML again; checksum commit is safely retried.
- Heads and downloads into Lambda-compatible temporary storage, then verifies
  expected size, downloaded size, MIME, file ID metadata, checksum metadata,
  S3 checksum header, and a locally recomputed SHA-256.
- Uses optimistic versions for `PROCESSING`, `READY`, and `FAILED`; a concurrent
  writer is never overwritten with a fabricated failure.
- Images get an aspect-ratio JPEG thumbnail in `thumbnails/<file_id>.jpg` plus
  structured detector/classifier output.
- Videos reuse exact one-frame-per-second sampling and maximum-simultaneous
  species-count aggregation.
- Dedup reservations become `COMMITTED` only after the `READY` record is saved.
- Failures persist stable non-sensitive codes. An uploaded thumbnail is removed
  if later image inference fails.
- Added the real Lambda bootstrap for DynamoDB, S3, the lazy supplied-model
  runtime, and OpenCV video sampling.

## Created files

- `backend/src/pacific_bioarchive/application/processing.py`
- `backend/src/pacific_bioarchive/handlers/__init__.py`
- `backend/src/pacific_bioarchive/handlers/media_processor.py`
- `backend/tests/unit/test_async_processing.py`
- `backend/uv.lock`
- `docs/stages/STAGE_3.2_REPORT.md`
- `docs/stages/STAGE_3.2_HANDOFF.md`

## Modified files

- `.gitignore`
- `backend/src/pacific_bioarchive/persistence/dynamodb.py`
- `backend/src/pacific_bioarchive/persistence/s3.py`
- `backend/tests/unit/test_domain_persistence.py`
- `docs/GENAI_USAGE.md`

## Verification

Command:

```powershell
uv run --project . --extra dev pytest -q
```

Observed result: `62 passed` (53 prior regression tests plus 9 asynchronous
processing tests).

Additional verification:

- Python bytecode compilation passed for all backend source and tests.
- Ruff checks passed for all new Stage 3.2 source and test files; repository-wide
  Ruff still reports pre-existing style findings and is not claimed clean.
- Repository secret-pattern scan returned no matches outside excluded legacy
  and virtual-environment paths.

New tests cover image success, video success, replay/idempotency, locally
recomputed checksum mismatch, malformed/wrong S3 events, thumbnail upload
failure, model failure and thumbnail cleanup, optimistic-version conflict, and
URL-decoded handler dispatch.

## Run notes

The AWS handler is
`pacific_bioarchive.handlers.media_processor.lambda_handler`. It requires
`PBA_MEDIA_BUCKET`, `PBA_MEDIA_TABLE`, `PBA_DEDUP_TABLE`, the three supplied ML
artifact path variables documented for Stage 1.1, and optional
`PBA_MAX_VIDEO_SAMPLES`.

## AWS operations

None in this stage. All S3/DynamoDB-facing behavior was tested through injected
adapters. Live event delivery is not claimed until the SAM deployment stage.

## Known issue and risk

The supplied real models still require a pinned Linux container dependency
stack and a successful detector-plus-classifier smoke test. The orchestration
boundary is real, but mocked inference is not evidence that the supplied model
runtime currently loads. S3 events are at-least-once; optimistic writes and
READY replay handling protect state, while later infrastructure must configure
only the `originals/` prefix to avoid thumbnail recursion.
