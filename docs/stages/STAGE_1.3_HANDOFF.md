# Stage 1.3 Handoff — Video Processing

## Added behavior

Videos now use one sample at every whole second, as explicitly required. Each
sample is passed through the same image inference service, and detections retain
their video timestamp.

## Files to understand

- `media/video_processing.py`
- `tests/unit/test_video_processing.py`
- ADR-010 in `docs/ARCHITECTURE_DECISIONS.md`

## Verification

1. Run all 24 backend tests.
2. Generate a 3.2-second 5-fps clip and verify timestamps `[0,1,2,3]`.
3. Confirm repeated counts `[1,2,1]` aggregate to `2`, not `4`.

## Demo questions

- How do you guarantee one frame per second rather than every frame?
- Why is maximum-per-frame count used instead of summing the video?
- What limits prevent a long video exhausting Lambda/free-plan resources?
- How can the examiner see which second produced a detection?

