# REST API Specification

Base URL is deployment output `ApiUrl`. Except for Cognito-managed registration,
verification, sign-in, federation callback, and static assets, every business
route requires `Authorization: Bearer <Cognito access/id JWT>`.

All timestamps are UTC ISO-8601. Errors use:

```json
{
  "error": {
    "code": "DUPLICATE_FILE",
    "message": "This file has already been uploaded.",
    "request_id": "...",
    "details": {}
  }
}
```

## Health

### `GET /health`

Authenticated lightweight deployment check. Returns `200` with service/version.

## Uploads

### `POST /uploads/init`

Input:

```json
{
  "filename": "camera-01.jpg",
  "content_type": "image/jpeg",
  "size_bytes": 123456,
  "checksum": "64 lowercase SHA-256 characters"
}
```

Returns `201` with `file_id`, private object key, required headers, and an
expiring presigned PUT URL. Returns `409 DUPLICATE_FILE` for an existing or
reserved checksum. Invalid type/size/checksum returns `400`.

### `GET /media/{file_id}`

Returns processing state and, when ready, metadata plus expiring original and
thumbnail URLs. The uploader can inspect their own pending/failed record; other
authenticated users see only `READY` media. `404` if unknown or intentionally
hidden. Detail metadata includes bounded detections, confidence evidence and
the configured `model_version` used for inference.

## Queries

### `POST /queries/tags`

Input:

```json
{"requirements": {"wombat": 2, "magpie": 1}}
```

Every value is an integer >=1. All requirements are logical AND. Returns ready
media; image entries contain thumbnail and original URLs, videos contain the
full video URL.

### `GET /queries/species?tag=dingo`

Equivalent to minimum count 1, including manual tag presence.

### `POST /queries/thumbnail`

Input: `{"thumbnail_url":"https://..."}`. The URL is normalized to an S3 key;
returns the corresponding expiring full-size URL or `404`.

### `POST /queries/file/init`

Input includes `filename`, `content_type`, `size_bytes`, and browser-computed
`checksum`, using the same image limits as upload but no dedup reservation.
Returns `query_id`, user-scoped `temp_key`, required signed headers, and a
short-lived presigned PUT URL.

### `POST /queries/file/{query_id}`

Input: `{"temp_key":"query-temp/<subject>/<query-id>/input.jpg"}`. The ML
function detects the temporary file's tags, queries ready media with logical
AND, and deletes the temp object in `finally`. Returns detected tags and matches.
It never creates a media/dedup record.

This execution route is integrated with the separate ML container Lambda rather
than the lightweight core API function. The function validates S3 metadata,
checksum header and downloaded SHA-256, and deletes the temporary object in
`finally` on success or failure. Cross-user/query keys return `400
TEMP_QUERY_FORBIDDEN` without deleting another user's object.

## Tag management

### `POST /media/tags`

Assignment-compatible input:

```json
{
  "urls": ["https://...", "https://..."],
  "tags": ["dingo", "night"],
  "operation": 1
}
```

`operation=1` adds and `operation=0` removes normalized manual tags from all
identified files. Removing absent tags is ignored. Returns a result per input;
malformed operation returns `400`.

The implementation also accepts stable `file_ids` for reliable UI calls while
retaining the URL request required by the assignment.

## Delete

### `POST /media/delete`

Input:

```json
{"urls": ["https://..."], "file_ids": ["optional-stable-id"]}
```

Deletes each original/video, thumbnail, media record, and dedup record.
Repeated deletion is idempotent. Returns per-item outcomes; unexpected partial
AWS failures return `500 DELETE_INCOMPLETE` and are logged without secrets.

## Notifications

### `POST /notifications/subscription`

Input: `{"tags":["dingo","wombat"]}`. Email is taken from the verified
Cognito claims, never trusted from request JSON. Creates/updates the SNS email
subscription/filter and returns `PENDING` until the user confirms the AWS email.
The success status is `202`; it means the request is pending, not that email
delivery has been confirmed.

### `GET /notifications/subscription`

Returns normalized watched tags and actual subscription status.

### `DELETE /notifications/subscription`

Removes the user's subscription record and unsubscribes a confirmed SNS ARN.
This destructive external action requires explicit user confirmation during
interactive setup/demo preparation.

## Media response shape

```json
{
  "file_id": "uuid",
  "filename": "camera-01.jpg",
  "file_type": "image",
  "species_counts": {"dingo": 2},
  "detections": [{"species":"dingo","combined_confidence":0.91}],
  "model_version": "supplied-v1",
  "auto_tags": ["dingo"],
  "manual_tags": ["night"],
  "all_tags": ["dingo", "night"],
  "processing_status": "READY",
  "thumbnail_url": "https://signed...",
  "original_url": "https://signed...",
  "created_at": "2026-08-23T00:00:00Z"
}
```

## Limits

- images: 10 MiB by default;
- videos: 50 MiB and 30 seconds by default for predictable demo/free-plan use;
- tags: 20 per request, 50 characters each;
- bulk URLs/IDs: 25 per request;
- query result page: 50 records, paginated thereafter.

Limits are configuration values and returned in validation errors/UI guidance.
