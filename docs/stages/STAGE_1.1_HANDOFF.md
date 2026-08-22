# Stage 1.1 Handoff — Reusable Inference Service

## Added behavior

`WildlifeInferenceService` now performs framework-neutral orchestration while
runtime adapters own heavyweight model loading. Business code can inject fakes,
so the rest of the system never imports PyTorch merely to run a query or test.

## Files to understand

- `ml/types.py` — stable contracts
- `ml/labels.py` — classifier output and canonical tag mapping
- `ml/inference.py` — count/crop/threshold behavior
- `ml/runtime.py` — lazy real-model adapters and environment configuration
- `tests/unit/test_inference.py` — executable behavior examples

## Verification

Run the 10 unit tests and inspect a serialized `InferenceResult`. A future
student assigned this stage must also rerun the documented real-model container
smoke test once the final dependency lock exists.

## Demo questions

- Why are detector and classifier interfaces separated?
- How are two detections of the same species counted?
- How is dingo normalized when two taxonomy rows map to it?
- Why is lazy model loading important in Lambda?
- How can the model version change without editing application code?

