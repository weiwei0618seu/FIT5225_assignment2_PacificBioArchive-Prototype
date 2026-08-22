# Four-Member Handoff Plan

This plan assigns coherent deltas, not four copies of the cumulative repository.
Use `25%` per member in the draft contribution table until the team agrees on
truthful percentages; no member may exceed 30%. Replace Member labels with real
names/IDs only after the students confirm them.

## Member 1 — ML and media intelligence (25%)

- Branches: `stage-0-baseline` through `stage-1.3-video-processing`, plus the
  real-model/CI portions of `stage-6.2-integration-e2e`.
- Focus files: `backend/src/pacific_bioarchive/ml/`, `media/`,
  `backend/Dockerfile.ml`, model smoke script/evidence and corresponding tests.
- Required verification: single-image real inference, species count, aspect-
  ratio thumbnail, exact one-frame-per-second video sampling, Linux image smoke.
- Must explain: no retraining, isolated TorchScript conversion, artifact hashes,
  warm-model singleton and video count semantics.
- Suggested official commit: `feat: integrate supplied wildlife ML and media processing`.

## Member 2 — Domain, queries and management API (25%)

- Branches: `stage-2.1-domain-persistence` through
  `stage-2.3-media-management`, plus `stage-4.1-rest-api`.
- Focus files: `domain/`, `application/queries.py`, `management.py`,
  `temp_queries.py`, `handlers/api.py`, `handlers/http.py`, persistence adapters
  used by these flows and tests.
- Required verification: atomic checksum reservation, strict AND/minimum counts,
  species, thumbnail and temporary-file queries, bulk tag add/remove, complete
  idempotent delete and safe API errors.
- Must explain: automatic versus manual tags, owner checks, stable object keys,
  presigned URL normalization and partial-delete reporting.
- Suggested official commit: `feat: add archive queries and bulk media management`.

## Member 3 — AWS eventing, notifications and infrastructure (25%)

- Branches: `stage-3.1-s3-upload-workflow` through
  `stage-3.3-notifications`, `stage-6.1-infrastructure`, and
  `stage-6.3-aws-deployment`.
- Focus files: S3/DynamoDB/SNS adapters, media processor handler,
  `infrastructure/`, OIDC/ECR workflow and live-AWS evidence.
- Required verification: checksum-bound presign, replay-safe S3 event,
  notification filter/dedup, least-privilege assertions, cfn-lint/SAM, reviewed
  change set and live stack outputs.
- Must explain: EventBridge prefix, SNS confirmation, OIDC subject restriction,
  immutable digest, Retain policy, 3008 MiB/Academy concurrency adaptations and
  free-plan boundary.
- Suggested official commit: `feat: deploy event-driven AWS storage and notifications`.

## Member 4 — Authentication, UI and final delivery (25%)

- Branches: `stage-4.2-cognito-iam`, all `stage-5.*` branches,
  `stage-6.2-integration-e2e` frontend/integration portions and final handoff.
- Focus files: `auth/`, `infrastructure/auth-and-iam.json`, `frontend/`, root
  README and final user/demo/report documentation.
- Required verification: register/verify/login/logout, protected pages/APIs,
  all UI modes/states, frontend test/build/lint, CloudFront deployment and live
  end-to-end demo rehearsal.
- Must explain: JWT issuer/audience validation, verified-email claims, Cognito
  code flow/PKCE, no browser AWS keys and optional Google federation boundary.
- Suggested official commit: `feat: add Cognito-protected web application and guides`.

## Every member must do personally

1. Download/check out the assigned branch and read its Stage Report/Handoff.
2. Run the assigned tests and retain honest output.
3. Trace one request through their code and make at least one understood review
   or correction where necessary.
4. Commit their owned delta with their own GitHub account to the private official
   repository; do not delegate all commits to one member.
5. Prepare the listed Q&A topics and participate in the demo/peer assessment.

