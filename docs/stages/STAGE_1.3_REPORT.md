# Stage 1.3 Report — Video Processing

## Goal

Extract exactly one frame per second, classify the samples through the existing
image inference boundary, and define defensible cross-frame species counts.

## Completed

- OpenCV sampler validates video metadata and decodes timestamps `0, 1, 2, ...`
  strictly below duration.
- Default maximum is 30 samples (30-second demo video limit).
- Safe errors cover invalid videos, metadata, overlong clips, failed frame
  reads, empty samples, and disordered timestamps.
- Per-frame detections retain their timestamp.
- Video species count is the maximum simultaneous count observed in any sampled
  second, avoiding repeated counting of one persistent animal.
- Model version consistency is enforced across a video.

## Automated tests

Full result: `24 tests passed` (19 regression + 5 video behavior tests).

Video tests cover exact duration boundaries, invalid/overlong duration,
cross-frame max aggregation, timestamp evidence, empty/disordered samples, and
model-version changes.

## Real OpenCV smoke

An isolated Python 3.12 environment with
`opencv-python-headless 4.14.0.94` generated a real 3.2-second, 5-fps MJPEG AVI.
`OpenCVFrameSampler` returned four 64x48 frames at `[0, 1, 2, 3]` seconds.

Result: `REAL_VIDEO_SMOKE=PASS`.

## Main files

- `media/video_processing.py`
- `tests/unit/test_video_processing.py`
- `backend/pyproject.toml` (`media` optional dependency)

## Known issues / later work

- The ML container must include an OpenCV build with codecs for the accepted MP4,
  MOV, and AVI formats.
- Upload size and decoded duration are both validated server-side in later
  processing stages.

## AWS operations

None.

