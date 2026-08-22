# Stage 6.1 Handoff — Serverless infrastructure and deployment controls

## What this stage owns

This stage owns the root SAM topology, cost/security defaults, deterministic
runtime definitions, isolated classifier conversion and guarded deployment
scripts. It does not own live AWS evidence.

## Main files

- `infrastructure/template.yaml` — complete deployable root stack.
- `infrastructure/auth-and-iam.json` — optional-Google nested identity/roles.
- `backend/Dockerfile.ml` — isolated classifier-build and final ML runtime.
- `backend/requirements-convert.txt` — build-only ONNX/protobuf-6 pins.
- `backend/requirements-ml.txt` — final MegaDetector/protobuf-3 pins.
- `backend/scripts/export_classifier.py` — numerical TorchScript conversion.
- `infrastructure/scripts/validate.ps1` — cumulative local quality gate.
- `infrastructure/scripts/deploy-core.ps1` — secret-free confirmed SAM deploy.
- `infrastructure/scripts/deploy-frontend.ps1` — output-driven SPA build/sync.
- `backend/tests/unit/test_infrastructure_template.py` — cost/security/template
  assertions.

## Verification

Run `./infrastructure/scripts/validate.ps1`. With SAM/Docker available also run:

```powershell
sam validate --lint --template-file infrastructure/template.yaml --region ap-southeast-2
sam build --template-file infrastructure/template.yaml --parallel
```

Expected current automated results: backend 103 tests and frontend 17 tests.

## Review questions

- Why are three S3 buckets private, including the frontend bucket?
- What creates HTTPS for Cognito/Google callbacks?
- Why does S3 publish through EventBridge rather than direct notification?
- Which settings bound cost and blast radius?
- Why are classifier conversion and detector runtime different build stages?
- How is numerical equivalence checked without retraining?
- Why can native auth deploy before Google, and what enforces Google secrets?
- Which retained resources require deliberate cleanup after assessment?

## Blockers before deployment

- Obtain a working Linux Docker/SAM build environment.
- Build the final image and run both supplied models on real fixtures.
- Inspect signed-in AWS Billing/Free Plan and generated change set.
- Obtain team-owned Google OAuth values only after exact redirect output exists.
- Never pass OAuth secrets through a committed file, terminal transcript or chat.
