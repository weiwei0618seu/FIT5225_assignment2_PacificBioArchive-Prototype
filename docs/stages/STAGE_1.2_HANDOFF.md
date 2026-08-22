# Stage 1.2 Handoff — Image Intake and Thumbnails

## Added behavior

The project can validate upload metadata before issuing a presigned URL, compute
the same SHA-256 in browser/server workflows, and create bandwidth-efficient
JPEG thumbnails without distorting the original image.

## Files to understand

- `media/validation.py` — trust boundary, type/size/name/checksum policy
- `media/checksum.py` — streaming dedup identity
- `media/image_processing.py` — thumbnail encoding policy
- `test_media_image.py` — boundary and corruption examples

## Verification

Run all 19 tests. Open a generated thumbnail in the test debugger and confirm
its dimensions retain the source ratio.

## Demo questions

- Why is filename-based deduplication insufficient?
- Why validate both MIME type and extension?
- How do thumbnails save bandwidth while retaining original access?
- What prevents path traversal through a filename?

