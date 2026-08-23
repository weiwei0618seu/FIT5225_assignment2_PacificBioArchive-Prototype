# Pacific BioArchive — Prototype

Pacific BioArchive is the FIT5225 Assignment 2 AWS Prototype: a Cognito-
protected, serverless wildlife media application. It accepts images/videos,
prevents duplicate bytes with SHA-256, creates image thumbnails, samples videos
at one frame per second, runs the supplied detector/classifier, stores searchable
metadata, supports four query modes, bulk tag/delete operations, watched-tag SNS
email and a complete React UI.

The teaching team confirmed in writing that one cloud provider is sufficient,
so this implementation is AWS-only despite older multi-cloud PDF wording.

## Current status

- all planned implementation branches through `stage-6.3-aws-deployment` exist
  in the Prototype repository;
- supplied weights are reused without retraining and three expected fixtures
  pass locally and in the Linux Lambda image;
- the immutable ML image is published to ECR by secret-free GitHub OIDC;
- backend: 121 tests, 89.39% domain/application coverage;
- frontend: 23 tests plus typecheck, production build and ESLint;
- CloudFormation/cfn-lint and security assertions pass;
- live AWS root-stack/UI/E2E evidence remains Stage 6.3's final gate and is not
  represented as successful until observed.

See [HD_RUBRIC_AUDIT.md](docs/HD_RUBRIC_AUDIT.md) for the honest evidence gap.

## Repository layout

```text
backend/                 Python domain, application, adapters, handlers and ML
frontend/                React + TypeScript SPA
infrastructure/          SAM/CloudFormation, OIDC/ECR and deploy scripts
legacy/PacificBioArchive supplied baseline weights, labels and original script
tests/fixtures/          supplied real wildlife images
docs/                    architecture, API/data/test/user/deploy/demo/handoffs
```

Every cumulative `stage-X.Y-*` branch is a passing project state through that
stage. `stage-0-baseline` preserves supplied assets; later branches add reusable
ML/media, domain, AWS adapters, API/auth, UI, integration and deployment in the
order recorded by [MASTER_PLAN.md](docs/MASTER_PLAN.md).

## Model pipeline

The model source of truth is:

- `legacy/PacificBioArchive/mdv5a.pt` — supplied MegaDetector;
- `legacy/PacificBioArchive/model.pt` — supplied classifier;
- `legacy/PacificBioArchive/labels.txt` — supplied 46-class map.

The classifier is converted to checked TorchScript during the isolated image
build; this is serialization compatibility, not training. The Lambda image uses
paths/version/thresholds from environment variables and exposes one reusable
inference service. Images return species counts, confidence evidence and
detections. Video counts use the maximum simultaneous count across exact
one-second samples to avoid counting the same animal again on every frame.

Run the real-model smoke after Git LFS objects are present:

```powershell
uv run --project backend --extra dev --extra media python backend/scripts/smoke_real_models.py
```

The pinned Linux build/run is in `.github/workflows/validate-and-smoke.yml`.

## Local quality gate

Install `uv`, Node.js and pnpm, then run:

```powershell
./infrastructure/scripts/validate.ps1
```

It runs backend tests/coverage/Ruff, frontend install/typecheck/tests/build/
ESLint, cfn-lint and SAM validation when the CLI is available. Individual
commands:

```powershell
uv run --project backend --extra dev pytest -q backend/tests
uvx ruff check backend
cd frontend
pnpm install --frozen-lockfile
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
```

## Frontend development

Copy the public identifiers from `.env.example` into ignored
`frontend/.env.local`, then:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm run dev
```

Routes are `/register`, `/verify`, `/login`, `/auth/callback`, and protected
`/`, `/upload`, `/search`, `/manage`. Google federation code is present but is
enabled only after native Cognito is stable and team-owned OAuth credentials are
configured outside Git.

## AWS deployment

Deploy only to `ap-southeast-2`, confirm the Free Plan before each mutation, and
review every change set. The architecture uses Cognito, private S3, Lambda,
HTTP API Gateway, on-demand DynamoDB, EventBridge, SNS, CloudWatch and CloudFront;
it contains no EC2/NAT/RDS/OpenSearch/SageMaker/EFS/WAF.

Follow [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md). The scripts require an
explicit `US$0`/confirmation switch and an immutable ECR `@sha256` URI. They do
not accept Google secrets or create long-lived AWS keys.

## Configuration

`.env.example` documents all non-secret backend and SPA variables. Important
rules:

- no `.env`, AWS key, password, JWT, presigned URL or OAuth secret in Git;
- no local absolute paths in runtime configuration;
- keep model path/version/thresholds configurable;
- use CloudFormation outputs for API, bucket, Cognito and CloudFront IDs;
- production browser configuration contains identifiers/URLs only.

## Main documentation

- [Architecture](docs/ARCHITECTURE.md) and
  [decisions](docs/ARCHITECTURE_DECISIONS.md)
- [API specification](docs/API_SPEC.md) and [data model](docs/DATA_MODEL.md)
- [Test plan](docs/TEST_PLAN.md) and [evidence index](docs/evidence/README.md)
- [User guide](docs/USER_GUIDE.md), [deployment guide](docs/DEPLOYMENT_GUIDE.md)
  and [demo plan](docs/DEMO_PLAN.md)
- [Generative AI usage](docs/GENAI_USAGE.md)
- [four-member handoff](docs/TEAM_HANDOFF_PLAN.md) and
  [official-repository integration](docs/OFFICIAL_REPO_INTEGRATION_PLAN.md)
- [visually verified Team Report draft](docs/report/README.md) with official AWS
  architecture icons (member IDs and live screenshots still required)
- per-stage reports/handoffs under `docs/stages/`

Before handoff, run `./scripts/verify-final-delivery.ps1`. The stricter
`-RequireFinalState` mode additionally requires sanitized live-stack/UI/E2E
evidence, the final Team Report PDF and a clean, pushed
`stage-7.1-final-handoff` branch; it is expected to fail until those real final
artifacts exist.

## Troubleshooting

- **Git LFS pointer/model load failure:** run `git lfs pull`, verify file sizes
  and compare hashes in `docs/evidence/`.
- **AWS 409 duplicate:** expected for identical bytes; query/use the existing
  record or upload different content.
- **Processing remains pending:** use a short supported file, inspect the media
  processor log and confirm the S3 EventBridge rule.
- **Temporary query remains pending:** inspect the temporary-query orchestrator
  and ML logs; the supplied model may take over two minutes on a cold CPU Lambda,
  so the browser polls instead of holding an HTTP request open.
- **401/redirect:** sign in again and verify deployed Cognito/API identifiers.
- **SNS remains PENDING:** open the AWS subscription email and confirm it.
- **Academy Lambda quota error:** use the current template (3008 MiB and no
  reserved concurrency); do not request paid capacity for this assessment.
- **CloudFront shows an older build:** wait for the invalidation and hard refresh.

## Repository safety

This is the Prototype repository only. Do not modify the official Group 8
repository from this workflow. Model weights use Git LFS; build output, local
environments, secrets and IDE caches are ignored. AWS, test and demo results are
reported only after they are actually observed.
