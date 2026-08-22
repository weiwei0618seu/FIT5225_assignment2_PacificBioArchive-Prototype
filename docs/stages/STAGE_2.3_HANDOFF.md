# Stage 2.3 Handoff — Bulk Tags and Complete Deletion

## Added behavior

The complete data-management Rubric behavior exists behind a reusable service.
URL inputs are normalized to private S3 keys, authorization is preflighted, and
all related artifacts are removed on successful delete.

## Files to understand

- `application/management.py`
- `application/references.py`
- `tests/unit/test_management.py`
- `DedupRepository.remove`

## Verification

Run all 47 tests. Verify the no-op removal case leaves the record version
unchanged and the complete image delete removes exactly three logical records:
original, thumbnail, and metadata/checksum state.

## Demo questions

- What does operation 0/1 mean?
- What happens if a requested delete tag is absent?
- How does bulk URL input map to records when URLs are signed?
- What is deleted for an image versus a video?
- How are partial S3/DynamoDB failures surfaced?

