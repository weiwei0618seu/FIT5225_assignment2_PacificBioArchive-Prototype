# Data Model

## Media table

Primary key: `file_id` (UUID string)

| Field | Type | Purpose |
|---|---|---|
| `file_id` | string | stable public-safe identifier |
| `owner_sub` | string | Cognito subject of uploader |
| `filename` | string | sanitized display filename |
| `checksum` | string | lowercase SHA-256 hex |
| `file_type` | `image`/`video` | processing and UI behavior |
| `content_type` | string | validated media MIME type |
| `size_bytes` | integer | upload limit and audit |
| `original_key` | string | private S3 key; durable location |
| `thumbnail_key` | string/null | image thumbnail key |
| `species_counts` | map<string,int> | canonical automatic tag counts |
| `auto_tags` | list<string> | keys of positive `species_counts` |
| `manual_tags` | list<string> | normalized user-supplied tags |
| `all_tags` | list<string> | union used by queries/notifications |
| `detections` | list<object> | bounded species/confidence evidence |
| `model_version` | string/null | inference artifact/configuration version used |
| `video_samples` | integer/null | number of one-second frames processed |
| `processing_status` | enum | `RESERVED/UPLOADED/PROCESSING/READY/FAILED` |
| `error_code` | string/null | safe machine-readable failure reason |
| `created_at` | ISO-8601 string | upload reservation time |
| `updated_at` | ISO-8601 string | last state/tag change |
| `version` | integer | optimistic update/versioning |

URLs are not persisted. Response serializers create short-lived
`original_url`/`thumbnail_url` values from keys.

## Dedup table

Primary key: `checksum`.

| Field | Purpose |
|---|---|
| `checksum` | atomic SHA-256 identity |
| `file_id` | owner media record |
| `owner_sub` | audit identity |
| `status` | `RESERVED` or `COMMITTED` |
| `expires_at` | DynamoDB TTL for abandoned reservations; omitted when committed |

A conditional put (`attribute_not_exists(checksum)`) makes concurrent duplicate
requests deterministic. The processor recomputes the uploaded bytes before
committing the reservation.

## Subscription table

Primary key: `user_sub`.

| Field | Purpose |
|---|---|
| `user_sub` | authenticated Cognito subject |
| `email` | verified destination claimed by Cognito token |
| `tags` | normalized watched tags |
| `sns_subscription_arn` | ARN or pending-confirmation marker |
| `status` | `PENDING/CONFIRMED/ERROR` |
| `updated_at` | audit timestamp |

## Temporary-query job table

Primary key: `query_id`. Items expire through DynamoDB TTL after one hour.

| Field | Purpose |
|---|---|
| `query_id` | stable random job identifier |
| `owner_sub` | owner-only polling and ML event binding |
| `temp_key` | exact S3 input bound at initiation |
| `status` | `AWAITING_UPLOAD/PROCESSING/READY/FAILED` |
| `species_counts` | detected canonical counts on success |
| `matched_file_ids` | stable result IDs, never signed URLs |
| `total` / `truncated` | result-page semantics |
| `model_version` | supplied-model version used |
| `error_code` | safe terminal failure code only |
| `expires_at` | one-hour TTL epoch |
| `version` | optimistic concurrency guard |

## Notification event item

The notification-events table has primary key `event_id`. Notification
idempotency uses a deterministic key
`file_id#record_version#sha256(sorted-matching-tags)`. It is conditionally
claimed before publish so an S3 retry does not send the same logical
notification twice. A failed publish releases its claim so a later Lambda
retry can try again.

## Query semantics

- automatic counts satisfy minimum-count requirements;
- a manual tag counts as present with effective count 1 for simple species
  queries, but does not fabricate an automatic animal count greater than one;
- multi-tag inputs require every tag condition (logical AND);
- temporary-file query uses the detected canonical tag set with minimum 1 and
  regenerates private URLs only when the owner polls a ready job;
- only `READY` media appears in normal results.
