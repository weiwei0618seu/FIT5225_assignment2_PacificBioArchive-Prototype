# Stage 2.1 Report — Domain and Persistence

## Goal

Create a framework-neutral media aggregate, atomic checksum reservations,
optimistic concurrency, and equivalent in-memory/DynamoDB persistence adapters.

## Completed

- `MediaRecord` covers all required metadata and processing states.
- Valid state helpers for processing, ready, failed, and manual-tag updates.
- Canonical automatic/manual/all-tag behavior and effective query counts.
- READY images require thumbnails; status/version/error invariants are enforced.
- Thread-safe in-memory media and dedup repositories.
- Atomic checksum reservation with abandoned-upload TTL replacement.
- Committed checksums cannot be silently released.
- DynamoDB conditional create/save/commit/release operations.
- DynamoDB pagination and Decimal-safe nested detection serialization.

## Tests

Result: `31 tests passed` (24 regression + 7 domain/persistence tests).

New coverage includes state transitions, canonical tags, READY invariants,
optimistic version conflict, idempotent deletion, duplicate reservation, TTL
expiry, commit/release safety, DynamoDB condition expressions, and nested
float/Decimal round trips.

## Main files

- `domain/media.py`
- `domain/repositories.py`
- `persistence/memory.py`
- `persistence/dynamodb.py`
- `tests/unit/test_domain_persistence.py`

## Known issues / later work

- DynamoDB tables and least-privilege roles are created in the infrastructure
  stage.
- Production query scale is intentionally bounded; pagination exists and query
  predicates are added next.
- Cross-resource S3/DynamoDB operations require compensating/idempotent service
  behavior because they cannot share one transaction.

## AWS operations

None; DynamoDB calls are adapter tests with injected fakes.

