# Stage 6.2 Report — Integrated regression and supplied-model proof

## Goal and boundary

Prove the cumulative system locally across security/API/data/media/UI boundaries
and remove the supplied-model uncertainty with real fixtures. Keep local/model,
Linux-container and live-AWS evidence explicitly separate.

## Real supplied-model result

The exact Git LFS source artifacts were used without retraining:

- MegaDetector SHA-256:
  `fe3e90e4b1955821ab7c1f88b446dc0c8cb25e109fdd1872916a55305294a5ef`
- source classifier SHA-256:
  `dfc99bd1e0c8b14c6755f4504460c414f678e72936d5f849f9947dff84ca913a`
- label map SHA-256:
  `793e7bfae8e08e380efdf8d1fec0ac85ef25b19ea4cc925649349e093d01be11`

The isolated converter produced TorchScript SHA-256
`a62ec6c769789386c02ce52342d93971cf4cd8754941caf4d1fc0258f7dcfebb`.
On Windows 11, Python 3.12.13, CPU-only, both supplied models then returned:

| Fixture | Expected/observed tag | Detector | Classifier | Combined |
|---|---|---:|---:|---:|
| `Alectura_lathami_1.JPG` | australian brushturkey ×1 | 0.961 | 0.999960 | 0.960961 |
| `Casuarius_casuarius_1.JPG` | southern cassowary ×1 | 0.957 | 1.000000 | 0.957000 |
| `Felis_catus_3.JPG` | domestic cat ×1 | 0.959 | 0.993952 | 0.953200 |

Warm three-fixture execution took 11.990 seconds total. Full hashes, bounding
boxes and per-fixture timings are in `docs/evidence/LOCAL_MODEL_SMOKE.json`.

## Integrated workflow result

Added one end-to-end backend regression using real fixture bytes and
deterministic inference. It crosses the actual handlers/services/adapters for:

1. verified-email watched-tag subscription;
2. checksum reservation and presigned required headers;
3. stored byte/checksum/MIME/metadata verification;
4. asynchronous image processing and thumbnail persistence;
5. automatic tag/count query and notification publish;
6. manual tag addition and manual-tag query;
7. full original/thumbnail/record/dedup deletion.

Added three frontend API boundary tests proving a fresh Cognito ID token is used,
responses are no-store, stable safe errors preserve request IDs, and an expired
local session prevents any fetch.

## Quality result

```powershell
uvx ruff check backend
# All checks passed

uv run --project backend --extra dev pytest -q backend/tests \
  --cov=pacific_bioarchive.domain --cov=pacific_bioarchive.application \
  --cov-report=term-missing --cov-fail-under=85
# 104 passed; 90.12% domain/application coverage

cd frontend
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
# 6 files, 20 tests; all commands passed

uvx --from cfn-lint cfn-lint infrastructure/template.yaml infrastructure/auth-and-iam.json
# exit 0, no findings

uvx zizmor .github/workflows/validate-and-smoke.yml
# No findings to report
```

Ruff also mechanically normalized existing import/export ordering and modern
typing across the cumulative backend; intentional broad deletion-adapter error
capture now has an explicit reason and scoped lint exemption.

## Linux container status

The local machine has no Docker/SAM CLI. A GitHub Actions workflow, available
manually and on code changes to this stage branch, runs the same quality gate,
verifies that LFS objects are real, builds the x86_64
Lambda image, executes both supplied models on all three fixtures in that Linux
image and publishes seven-day model/image evidence artifacts. All Actions are
pinned to immutable commits, checkout credentials are not persisted and workflow
permissions are read-only. The stage is not allowed to call this passed until an
actual run is observed and linked here.

### First Linux attempt and remediation

[Run #1](https://github.com/weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype/actions/runs/32593231468)
on commit `a6bc151f396e17fde5e97938528812ded4791555` passed the complete
quality job but failed the image build honestly with `[Errno 28] No space left
on device`. The PyPI Linux Torch wheels had selected CUDA 12 packages despite
the CPU-only runtime design, and the two build stages exhausted the hosted
runner while installing them. No model smoke or artifact step ran.

Both build environments now use the official PyTorch x86_64 CPU wheels by
direct URL and SHA-256, avoiding both CUDA bloat and extra-index dependency
confusion. `uv pip compile` then resolved both Python 3.12 Linux requirement
sets successfully. All workflow actions were also upgraded to immutable Node 24
revisions so the rerun does not retain the first run's Node 20 deprecation
warning.

[Run #2](https://github.com/weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype/actions/runs/32593745736)
on commit `9a194c4a1fb27b69ef1b1f4f75eb4cc46eb85820` again passed the
quality job. The CPU runtime dependencies installed successfully, the supplied
classifier converted on Linux and passed the `[1, 46]` build check, proving the
disk remediation. The image then failed only at its final cache cleanup because
the minimal Lambda AL2023 base image does not contain the GNU `find` command;
no model smoke or artifact step ran. The cleanup now uses Python `pathlib` and
`shutil`, retaining a minimal base image without adding an operating-system
package solely for cleanup.

[Run #3](https://github.com/weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype/actions/runs/32594049095)
on commit `89c79b6c00f3e177c71b12fac7280031aef82a68` passed the quality
job and completed the full image build. The smoke command then failed before
loading either model because overriding the Lambda entrypoint to execute a
script mounted under `/tmp` did not automatically add the application location
`/var/task` to Python's import path. No model result or artifact was recorded.
The container smoke now supplies `PYTHONPATH=/var/task` explicitly; production
Lambda execution continues to use the base image's standard runtime entrypoint.

[Run #4](https://github.com/weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype/actions/runs/32594457374)
on commit `22aedf5323f379d8e3cc1e6a4b3f14d109dac9fa` passed quality and
again built the image. The smoke script imported the application and began the
first supplied fixture, but MegaDetector's transitive GUI `opencv-python`
distribution had overwritten the pinned headless `cv2`; importing it failed on
the Lambda base image's intentionally absent `libxcb.so.1`. No model result or
artifact was recorded. The GUI distribution is now version-pinned for stable
resolution, checked with the rest of the dependency graph, then removed in the
same image layer and replaced by the pinned headless wheel. An explicit `cv2`
version/import assertion protects this server-safe substitution without adding
X11 libraries or GUI surface to the Lambda image.

## AWS operations and cost

None. No AWS credentials are used by the CI definition, and no AWS resource or
cost was created by the local evidence.
