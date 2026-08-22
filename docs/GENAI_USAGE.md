# Generative AI Usage Log

This document must remain in the project and be updated throughout development.
The assessment requires an explicit Generative AI declaration even if AI use is
limited.

## Tool

- OpenAI Codex (`gpt-5.6-sol`) in the Codex desktop application.

## Uses to date

- Read and cross-checked the assignment specification and marking rubric.
- Audited the supplied ML weights, labels, test images, Python script, and
  dependency metadata.
- Assisted with architecture planning, source-code implementation, tests,
  infrastructure-as-code, documentation, and debugging in the private
  Prototype repository.
- Implemented and reviewed the Stage 3.2 S3-event processing orchestration,
  including adversarial checksum, replay, storage, model, and concurrency tests.
- Implemented Stage 3.3 Cognito-bound SNS subscription/filter state and
  deterministic notification-event deduplication, then verified pending,
  confirmation, replay, failure/retry, automatic-tag and manual-tag paths.
- Implemented Stage 4.1 HTTP API v2 parsing, claim propagation, safe error
  contracts, complete REST routing and isolated temporary-query ML execution;
  tested every route family plus authentication, cleanup and error redaction.
- Implemented and linted the Stage 4.2 Cognito/Google/OAuth and least-privilege
  IAM CloudFormation subtemplate, with automated assertions for registration,
  verification, PKCE-compatible client settings, secret handling and role
  separation.
- Created and browser-tested the Stage 5.1 React/TypeScript authentication
  experience, including required-attribute registration, confirmation-code
  verification, native and Google entry points, protected routing, restored
  sessions, logout, responsive desktop/mobile styling and component tests.
- Implemented the Stage 5.2 typed authenticated API client and full upload UI:
  local validation and SHA-256, duplicate-aware reservation, presigned S3 PUT
  progress, bounded asynchronous polling, recoverable failure states and
  structured image/video wildlife results.
- Implemented and tested the Stage 5.3 four-mode query workspace: normalized
  minimum-count AND search, species/manual-tag search, thumbnail-to-original
  lookup, ephemeral image inference with signed upload and cleanup-aware
  messaging, plus complete/empty/truncated result states.
- Completed the Stage 5.4 owner-management and notification UI with selectable
  bulk tag changes, explicit-confirmation complete deletion, per-item outcomes,
  verified-Cognito-email SNS watch creation/status/removal, and automated tests
  for destructive gating and honest pending status.
- Designed and linted the Stage 6.1 SAM/CloudFormation stack, private CloudFront
  SPA origin, bounded Lambda/EventBridge/DynamoDB/S3/SNS resources, cost guards,
  deployment scripts and infrastructure tests. Diagnosed the supplied-model
  protobuf conflict and implemented a numerically verified, no-retraining
  build-stage conversion from the supplied classifier pickle to TorchScript.

## Human accountability

All four students must read, run, test, explain, and where appropriate modify
the code they later contribute to the official repository. AI-generated or
AI-assisted output is not treated as evidence of correctness until a recorded
test has passed. AWS deployment status, test results, and screenshots must not
be fabricated.

## Ongoing log

Each stage report records the generated/modified files, commands executed,
results observed, known limitations, and the checks students should repeat.
