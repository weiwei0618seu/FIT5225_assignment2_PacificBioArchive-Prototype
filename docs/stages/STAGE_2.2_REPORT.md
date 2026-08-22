# Stage 2.2 Report — Query Engine

## Goal

Implement every assignment query predicate correctly and independently from
HTTP/AWS serialization.

## Completed

- Minimum-count tag queries with inclusive `>=` boundaries.
- Strict logical AND for every requested tag.
- Simple species queries using effective minimum count 1.
- Manual tags represent presence (count 1) but cannot fabricate larger animal
  counts.
- Only `READY` records are returned.
- Deterministic sort, bounded limits, totals, and truncation evidence.
- Temporary inference queries require every detected canonical tag at count 1.
- Virtual-hosted, path-style, signed, and direct thumbnail references normalize
  to stable S3 keys; wrong buckets, traversal, wrong prefixes, and schemes fail.

## Tests

Result: `41 tests passed` (31 regression + 10 query tests).

New coverage explicitly proves AND rather than OR, equality boundaries, manual
tag semantics, processing exclusion, no-result behavior, truncation, temporary
tag-set behavior, signed thumbnail lookup, bucket validation, and unsafe URLs.

## Main files

- `application/queries.py`
- `tests/unit/test_queries.py`

## Known issues / later work

- API serialization will replace object keys with short-lived presigned URLs.
- The assignment-scale DynamoDB scan is paginated but intentionally not a
  production-scale inverted tag index; see ADR-006.
- The temporary object's deletion guarantee belongs to the S3/application
  workflow stage, not this pure predicate layer.

## AWS operations

None.

