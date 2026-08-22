# Stage 1.1 Report — Reusable Inference Service

## Goal

Replace the import-time batch workflow with a reusable, lazy-loaded inference
boundary that returns structured detections and species counts.

## Completed

- Added typed detector/classifier protocols and serializable inference results.
- Added safe normalized bounding-box clipping and crop extraction.
- Added a 46-class label parser matching the supplied output ordering.
- Canonicalized both supplied dingo taxa to `dingo` and blank `Rattus` common
  name to `rattus`.
- Added deterministic confidence thresholds, maximum detections, structured
  counts, scientific names, confidences, and pixel boxes.
- Added lazy MegaDetector and onnx2torch/PyTorch runtime adapters. Heavy modules
  are imported only on first inference and models are reused for warm calls.
- Added environment-driven model paths/version/thresholds/CPU selection.
- Added Python package/test configuration.

## Created files

- `backend/pyproject.toml`
- `backend/src/pacific_bioarchive/ml/{types,labels,inference,runtime}.py`
- `backend/tests/unit/test_labels.py`
- `backend/tests/unit/test_inference.py`

## Test command

```powershell
$env:PYTHONPATH=(Resolve-Path backend/src).Path
python -m unittest discover -s backend/tests -p 'test_*.py' -v
```

## Test result

`10 tests passed` under Python 3.12. Tests cover class-map integrity, duplicate
dingo normalization, blank label fallback, structured multi-animal counts,
confidence thresholds, malformed/out-of-bounds boxes, deterministic detection
limits, serialization, and invalid configuration.

## Real model status

Both supplied weight archives are structurally valid, but the original
unversioned two-line requirements currently produce a protobuf/ONNX resolver
conflict on Windows Python 3.12. No real-inference success is claimed yet. The
Linux ML container dependency lock and real model smoke test remain mandatory
before AWS processing is marked complete.

## How to run

Use the unit-test command above. Real runtime construction requires these
environment variables:

- `PBA_DETECTOR_MODEL_PATH`
- `PBA_CLASSIFIER_MODEL_PATH`
- `PBA_LABELS_PATH`
- optional `PBA_MODEL_VERSION`, thresholds, and `PBA_FORCE_CPU`

## AWS operations

None.

## Risks

- Actual Linux dependency versions must be frozen after a passing model smoke.
- CPU latency and memory must be measured before Lambda limits are finalized.

