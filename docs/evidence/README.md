# Evidence index

Evidence files are machine-readable observations, not assertions inferred from
source code. They contain no credentials, JWTs, signed URLs, email codes or
Google values.

- `LOCAL_MODEL_SMOKE.json` — observed Windows/Python 3.12 CPU execution of the
  supplied MegaDetector and supplied classifier-derived TorchScript on three
  supplied real fixtures. It includes source/derived artifact hashes, fixture
  hashes, timings, counts, detections, confidences and model version.

The derived TorchScript file lives only under ignored `tmp/`; it is reproduced
from the Git LFS source classifier during the container build. Its evidence hash
does not replace the committed source-model hash.

Live AWS evidence belongs in a separate Stage 6.3 file and must only be added
after observing the deployed account. Never manufacture URLs, resource IDs,
cost values, email status or CloudWatch results.
