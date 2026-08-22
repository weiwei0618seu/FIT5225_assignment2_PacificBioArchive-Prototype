# Stage 2.3 Report — Bulk Tags and Complete Deletion

## Goal

Implement assignment-compatible bulk manual tag edits and coordinated deletion
of every storage/database/dedup artifact.

## Completed

- Accepts multiple signed original/thumbnail URLs and stable file IDs.
- `operation=1` adds normalized manual tags; `operation=0` removes them.
- Removing an absent tag is a successful no-op and does not create a needless
  version update.
- Validates operation, tag count/type/length, item limits, paths, bucket, and
  ownership before mutation.
- Only the uploader can mutate or delete media.
- Image deletion removes original + thumbnail; video deletion removes original.
- Media record and committed checksum entry are also removed.
- Repeated deletion is idempotent and reports `already_absent`.
- Storage failures keep metadata when possible and return
  `DELETE_INCOMPLETE` rather than pretending success.
- Shared S3 reference normalizer is now used by queries and management.

## Tests

Result: `47 tests passed` (41 regression + 6 management tests).

New coverage includes bulk mixed ID/URL add, removal of absent tags, no-op
version behavior, invalid input, not-found/owner preflight, complete image/video
cleanup, checksum cleanup, repeated deletion, and simulated storage failure.

## Main files

- `application/management.py`
- `application/references.py`
- `domain/storage.py`
- dedup `remove` methods in memory/DynamoDB adapters
- `tests/unit/test_management.py`

## Known issues / later work

- S3 has no transaction spanning DynamoDB. Partial failures are visible and
  logged; repair/retry behavior will be integrated in Lambda handlers.
- Newly added watched tags will feed the notification service in Stage 3.3.

## AWS operations

None.

