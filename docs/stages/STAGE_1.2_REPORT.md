# Stage 1.2 Report — Image Intake and Thumbnails

## Goal

Implement deterministic SHA-256 checksums, strict image/video metadata
validation, safe filenames, and compressed aspect-ratio-preserving thumbnails.

## Completed

- Streaming file/bytes SHA-256 independent of filename.
- Strict 64-character checksum normalization.
- Allowlisted MIME/extension pairs for JPG, PNG, WEBP, MP4, MOV, and AVI.
- Configurable 10 MiB image and 50 MiB video defaults.
- Path/control-character-safe bounded filenames.
- EXIF-aware thumbnails with LANCZOS resizing, no upscaling, transparency
  compositing, RGB conversion, progressive optimized JPEG output, and safe
  invalid-image errors.

## Tests

Command:

```powershell
$env:PYTHONPATH=(Resolve-Path backend/src).Path
python -m unittest discover -s backend/tests -p 'test_*.py' -v
```

Result: `19 tests passed` (10 regression + 9 new media tests).

Coverage includes same bytes under different filenames, streaming chunk sizes,
path sanitization, MIME mismatch, byte limits, checksum validation, landscape,
portrait, small/no-upscale, alpha transparency, compression, and corrupt input.

## Main files

- `media/checksum.py`
- `media/validation.py`
- `media/image_processing.py`
- `tests/unit/test_media_image.py`

## Known issues / later work

- Server-side upload processing must recompute the checksum and compare it with
  the browser claim.
- Video duration/content validation is added with the video stage.
- S3 keys must use generated IDs rather than sanitized filenames alone.

## AWS operations

None.

