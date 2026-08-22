# Stage 3.1 Report — S3 Upload Workflow

## Goal

Create an authenticated checksum-first private S3 upload flow that is race-safe,
size/type constrained, and recoverable when URL generation fails.

## Completed

- Validates actor, filename, MIME/extension, size, and SHA-256 before AWS calls.
- Reserves checksum conditionally before creating the media record.
- Uses UUID-style generated IDs and `originals/<file_id>/<safe-name>` keys.
- Presigned PUT binds content type, S3 SHA-256 checksum, file ID, and checksum
  metadata headers.
- Reservation outlives the shorter presigned upload URL.
- Duplicate bytes are rejected before a second record or URL is issued.
- Media/reservation state is rolled back if record creation or presigning fails.
- Added private S3 presigned GET/head/download/upload/delete adapter.
- Thumbnail uploads request SSE-S3 in addition to bucket default encryption.

## Tests

Result: `53 tests passed` (47 regression + 6 upload/S3 tests).

New coverage includes success state, same bytes/different filename duplicate,
validation-before-AWS, presign rollback, bound checksum headers, and private
bucket scoping for all S3 operations.

## Main files

- `application/uploads.py`
- `domain/storage.py`
- `persistence/s3.py`
- `tests/unit/test_uploads_s3.py`

## Known issues / later work

- The S3 processor must recompute checksum/size/MIME and compare metadata before
  committing dedup state.
- S3 CORS must allow the exact signed request headers from the deployed UI.
- Live presigned PUT is verified only after infrastructure exists.

## AWS operations

None; S3 client calls use an injected fake.

