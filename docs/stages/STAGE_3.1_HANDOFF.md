# Stage 3.1 Handoff — S3 Upload Workflow

## Added behavior

An authenticated user can obtain a private S3 upload ticket only after a global,
conditional SHA-256 reservation succeeds. The browser must send the returned
headers exactly, allowing S3 itself to validate transmitted bytes.

## Files to understand

- `application/uploads.py`
- `persistence/s3.py`
- `tests/unit/test_uploads_s3.py`

## Verification

Run all 53 tests. Inspect the presign test to see that hex SHA-256 becomes the
base64 `x-amz-checksum-sha256` required by S3.

## Demo questions

- At what point is duplicate content rejected?
- What happens if two requests race?
- Why are URL expiry and reservation TTL different?
- Which headers must the frontend send to the presigned URL?
- What cleanup occurs if presigning fails?

