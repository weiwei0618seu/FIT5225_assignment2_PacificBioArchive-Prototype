# Evidence index

Evidence files are machine-readable observations, not assertions inferred from
source code. They contain no credentials, JWTs, signed URLs, email codes or
Google values.

- `LOCAL_MODEL_SMOKE.json` — observed Windows/Python 3.12 CPU execution of the
  supplied MegaDetector and supplied classifier-derived TorchScript on three
  supplied real fixtures. It includes source/derived artifact hashes, fixture
  hashes, timings, counts, detections, confidences and model version.
- `LINUX_MODEL_SMOKE.json` — the corresponding observed Linux/Python 3.12 CPU
  result from GitHub Actions run `32594837754` on commit `24e54bb`; all three
  supplied fixtures matched their expected species.
- `LINUX_CONTAINER.json` — the immutable local image ID, byte size,
  architecture and OS printed by the same successful CI job.

The derived TorchScript file lives only under ignored `tmp/`; it is reproduced
from the Git LFS source classifier during the container build. Its evidence hash
does not replace the committed source-model hash. The Windows and Linux
TorchScript serializations have different hashes, while the committed source
classifier hash, fixture hashes and observed numerical outputs remain bound and
equivalent. Both derived hashes are recorded rather than treated as source
identity.

The original seven-day artifact is
[`linux-container-evidence-32594837754`](https://github.com/weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype/actions/runs/32594837754/artifacts/9481320017)
(artifact ID `9481320017`, ZIP SHA-256
`cb13f98b49dd8e781b95bcb714a8d7bf399bdff7f4ea6b8132c4958e1e2b4ba8`).
The two Linux JSON files above preserve its observed content after expiry.

Live AWS evidence belongs in a separate Stage 6.3 file and must only be added
after observing the deployed account. Never manufacture URLs, resource IDs,
cost values, email status or CloudWatch results.

Observed Stage 6.3 evidence:

- `DEPLOYMENT_TOOLCHAIN_ACCEPTANCE.txt` records the official SAM Python 3.12
  container, pnpm 11.19.0, free-plan preflight and failed-stack deletion gate.
- `LIVE_STACK_ACCEPTANCE.txt` records the reviewed change set, successful root
  stack, frontend publication and sanitized ten-item live acceptance result.
- `live-ui/` contains empty-field registration/login screenshots plus a
  sanitized authenticated real-model image/thumbnail result. Query-management,
  logout and human SNS-confirmation/delivery evidence remain pending.

`LIVE_E2E.json` is deliberately absent until the complete live workflow has
been observed. Before it can satisfy the final gate, run:

```powershell
./scripts/verify-live-e2e-evidence.ps1
```

The file must use schema version 1, name every required check with its evidence
source and a short sanitized note, and record the Cognito verification, SNS
confirmation and watched-tag delivery as human observations. The validator
rejects endpoints, AWS ARNs, tokens, credentials, signed-request fields and
email addresses rather than attempting to redact them after they are committed.
