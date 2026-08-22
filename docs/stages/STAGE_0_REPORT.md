# Stage 0 Report — Supplied ML Baseline

## Goal

Preserve and audit the supplied wildlife ML prototype and test data without
claiming that the original batch script is production-ready.

## Completed

- Preserved the original Python script, configuration, README, label map, and
  both PyTorch weights under `legacy/PacificBioArchive/`.
- Preserved 30 real camera-trap JPG fixtures under `tests/fixtures/images/`.
- Configured Git LFS for `.pt`, `.onnx`, and `.pth` model artifacts.
- Added repository hygiene for secrets, IDE files, generated media, and build
  output.
- Verified both model archives with ZIP CRC checks and SHA-256 checksums.
- Verified all 30 real images can be decoded, contain no byte-identical
  duplicates, and map to supported class names.
- Verified the supplied script is syntactically valid under Python 3.12.

## Model evidence

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `model.pt` | 211,878,007 | `dfc99bd1e0c8b14c6755f4504460c414f678e72936d5f849f9947dff84ca913a` |
| `mdv5a.pt` | 280,767,041 | `fe3e90e4b1955821ab7c1f88b446dc0c8cb25e109fdd1872916a55305294a5ef` |

The classifier contains `onnx2torch` graph modules; the detector contains the
MegaDetector/YOLOv5 model classes. Both archives passed CRC validation.

## Test-data evidence

- 30 real JPG files
- 13 represented classifier classes
- no unreadable images
- no duplicate SHA-256 hashes
- image dimensions range from 1000–6144 px wide and 722–3456 px high

macOS `__MACOSX` resource-fork files from the ZIP were intentionally excluded.

## Commands used

```text
python -m py_compile legacy/PacificBioArchive/batch.py
python (Pillow/ZIP/hash audit scripts)
git lfs install --local
```

## Result

The supplied assets are sufficient to begin engineering. The original script
is a reference baseline, not a deployable service.

## Known issues to fix in Stage 1

- Script executes at import time and assumes a fixed working directory.
- Model/config/input/output paths are hard-coded.
- Inference prints results and opens Matplotlib instead of returning structured
  species counts/detections.
- Dependencies are unpinned; current `megadetector` and `onnx2torch` resolver
  constraints conflict around protobuf/ONNX on Python 3.12.
- The common-name map contains two dingo taxonomy entries and one blank common
  name (`Rattus`); canonical tag behavior must be explicit.
- No unit tests, video processing, thumbnail generation, or serverless adapter
  exists yet.

## AWS operations

None. No cloud resource was created in this stage.

