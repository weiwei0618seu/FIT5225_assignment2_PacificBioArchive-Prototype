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
- three local real fixtures match their expected classes with high confidence.

## Review questions

- Which hashes bind the result to the exact supplied detector/classifier?
- Is TorchScript conversion retraining? Why not?
- What numerical and shape checks guard the conversion?
- Which test crosses upload, processing, query, notification and deletion?
- How is a local model result distinguished from a Linux container result?
- What prevents the CI workflow from accessing AWS?

## Remaining gate

Observe a successful `Validate and smoke ML container` Actions run and
record its run URL, commit SHA, Linux image ID/size/architecture and smoke output.
If it fails, fix and rerun; never re-label a partial run as passing.
