# Stage 3.2 Handoff — Asynchronous Media Processing

## What this stage owns

This stage is the trust boundary between an untrusted browser upload and a
queryable `READY` media record. It validates the actual private S3 object,
invokes the image or exact-1-fps video pipeline, uploads image thumbnails, and
commits both media and dedup state.

## Main files to understand

- `application/processing.py` — validation, status transitions, cleanup and
  result persistence.
- `handlers/media_processor.py` — S3 event parsing and AWS runtime composition.
- `tests/unit/test_async_processing.py` — success, replay, integrity and failure
  evidence.
- `persistence/s3.py` — checksum-enabled `HeadObject`.
- `persistence/dynamodb.py` — retry-safe checksum commit.

## How to verify

From `backend`, run `uv run --project . --extra dev pytest -q` and confirm all
62 tests pass. Read the checksum-mismatch test to see that trusted ticket
metadata alone is insufficient: the downloaded bytes are hashed again.

## Likely demo/review questions

- Why is the browser-provided checksum verified again inside Lambda?
- Why can S3 invoke the same event more than once, and what makes the handler
  idempotent?
- Why is video count a per-species maximum across sampled frames rather than a
  sum?
- What happens if the thumbnail succeeds but model inference fails?
- How does an optimistic-version conflict avoid corrupting a newer record?
- Why must the S3 notification filter include only `originals/`?

## Student follow-up

Before contributing this stage to the official repository, the assigned member
must rerun the tests, inspect the safe failure codes, and later verify one real
image and one real short video through the deployed S3 event path. Do not claim
that live ML or AWS processing passed until that evidence exists.
