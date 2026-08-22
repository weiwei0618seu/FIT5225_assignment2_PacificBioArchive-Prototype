# Stage 6.2 Handoff — Integrated regression and supplied-model proof

## What this stage owns

This stage owns reproducible real-model smoke evidence, the complete local
business-flow regression, authenticated frontend client tests, full backend
Ruff cleanliness and the no-AWS-secret Linux image CI workflow.

## Main files

- `backend/scripts/smoke_real_models.py` — hash-bound multi-fixture runner.
- `docs/evidence/LOCAL_MODEL_SMOKE.json` — observed local model output.
- `backend/tests/integration/test_end_to_end_workflow.py` — full local flow.
- `frontend/src/api/client.test.ts` — authenticated request boundary.
- `.github/workflows/validate-and-smoke.yml` — manual Linux image proof.

## Current verification

- backend: 104 tests, 90.12% domain/application coverage and Ruff pass;
- frontend: 20 tests, typecheck, production build and ESLint pass;
- both CloudFormation templates pass cfn-lint;
- the pinned, read-only GitHub Actions workflow passes zizmor with no findings;
- three local real fixtures match their expected classes with high confidence;
- GitHub Actions run `32594837754` also passed both jobs and reproduced the same
  three species in the Linux/amd64 Lambda image; immutable image and smoke JSON
  are preserved under `docs/evidence/`.

## Review questions

- Which hashes bind the result to the exact supplied detector/classifier?
- Is TorchScript conversion retraining? Why not?
- What numerical and shape checks guard the conversion?
- Which test crosses upload, processing, query, notification and deletion?
- How is a local model result distinguished from a Linux container result?
- What prevents the CI workflow from accessing AWS?

## Completed gate

The required `Validate and smoke ML container` gate passed on run
[`32594837754`](https://github.com/weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype/actions/runs/32594837754),
commit `24e54bb0d220b8b7548e758f39e4cec54716d165`. Do not confuse this
portable-container proof with live AWS deployment; that remains Stage 6.3.
