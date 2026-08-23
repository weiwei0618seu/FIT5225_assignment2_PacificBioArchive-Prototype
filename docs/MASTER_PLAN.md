# Pacific BioArchive Master Plan

## Objective and success bar

Build a stable, demonstrable AWS serverless wildlife media platform that meets
every fully-implemented row in the FIT5225 Assignment 2 rubric. The target is
HD, so the implementation also includes federated Google sign-in after all core
features are stable.

The instructor's written AWS-only clarification is treated as the authority for
the provider scope. A copy of that clarification must be retained by the team
for the final report. The official repository remains out of scope until the
Prototype is complete and the four students begin their real integration work.

## End-to-end system flow

1. A user registers or signs in through Amazon Cognito.
2. The browser computes a SHA-256 checksum and requests an authenticated
   presigned S3 upload.
3. A conditional DynamoDB reservation rejects duplicate content before upload.
4. S3 receives the media and invokes the media-processing Lambda.
5. The processor verifies the checksum, creates an image thumbnail or samples a
   video at exactly one frame per second, runs MegaDetector + species
   classification, and stores structured counts/URLs/status in DynamoDB.
6. Authenticated APIs support tag/count AND queries, species queries,
   thumbnail-to-original lookup, temporary-file similarity queries, bulk tag
   edits, deletion, and notification subscriptions.
7. SNS sends confirmed subscribers a notification when a watched automatic or
   manually added tag appears.
8. The React UI exposes all rubric workflows with loading, success, error,
   unauthorized, duplicate, and empty-result states.

## Recommended AWS architecture

- **Cognito User Pool** — registration, email verification, login/logout, JWTs,
  optional Google federation.
- **S3 media bucket** — private originals, thumbnails, and query-temp objects.
- **S3 model bucket** — versioned detector/classifier artifacts.
- **API Gateway HTTP API** — RESTful routes protected by a Cognito JWT authorizer.
- **Lambda API function** — upload orchestration, queries, tag management,
  deletion, and subscription management.
- **Lambda ML container functions** — asynchronous media processing and
  temporary-file inference using the provided models.
- **Temporary-query orchestrator Lambda** — bridges S3 events to long ML
  inference without holding an API Gateway request open.
- **DynamoDB media table** — media metadata and processing state.
- **DynamoDB dedup table** — atomic checksum reservations with TTL.
- **DynamoDB subscriptions table** — user/tag/SNS subscription state.
- **DynamoDB temporary-query table** — owner-scoped, one-hour TTL polling state.
- **SNS topic** — tag-filtered email notifications.
- **CloudWatch** — structured logs, alarms, and short log retention.
- **S3 static web hosting** — deployable React SPA; protected routes redirect
  unauthenticated visitors while all data APIs and media URLs remain private.

## Cost guardrails

- Deploy only to `ap-southeast-2`.
- Never upgrade the AWS Free Plan.
- Avoid NAT Gateway, EC2, RDS, OpenSearch, SageMaker, WAF, EFS, and long-running
  containers.
- Use on-demand DynamoDB, short-lived Lambdas, API throttling, upload limits, and
  seven-day CloudWatch retention. Do not reserve Lambda concurrency on Academy
  accounts that expose only AWS's minimum unreserved pool.
- Use short demo videos and bounded frame extraction.
- Apply S3 lifecycle cleanup to query-temp and failed uploads.
- Tag every resource with `Project=PacificBioArchive` and `Environment=prototype`.
- Configure cost/free-tier alerts before load testing.

## Data model summary

See `docs/DATA_MODEL.md`. Durable records store S3 object keys rather than
public URLs. APIs issue expiring presigned URLs at response time.

## API summary

See `docs/API_SPEC.md`.

## UI page inventory

1. Register and email-verification guidance
2. Login and Google federated login
3. Dashboard/navigation and logout
4. Upload image/video with checksum progress and duplicate feedback
5. Search form for species and minimum-count AND queries
6. Results grid with thumbnails and clickable originals/video URLs
7. Thumbnail URL lookup
8. Temporary-file similarity query
9. Bulk tag management
10. Bulk deletion with confirmation
11. Notification subscription/status
12. Processing-status view and recoverable error feedback

## Sequential branch plan

Every branch inherits the previous passing branch. A branch is a cumulative,
reviewable system state—not an isolated patch.

| Order | Branch | Scope | Completion evidence |
|---:|---|---|---|
| 0 | `stage-0-baseline` | Preserve/audit supplied ML assets | hashes, fixtures, LFS, baseline docs |
| 1 | `stage-1.1-inference-service` | Lazy structured image inference and label normalization | mocked unit tests plus real model smoke test when dependencies resolve |
| 2 | `stage-1.2-image-processing` | SHA-256, validation, aspect-ratio thumbnail/compression | deterministic image tests |
| 3 | `stage-1.3-video-processing` | exactly 1 fps sampling and aggregated species counts | generated-video tests |
| 4 | `stage-2.1-domain-persistence` | domain entities, repository ports, in-memory/DynamoDB adapters | CRUD and conditional dedup tests |
| 5 | `stage-2.2-query-engine` | species, minimum count AND, thumbnail lookup, temp-query semantics | query edge-case tests |
| 6 | `stage-2.3-media-management` | bulk tag add/remove and complete idempotent deletion | management tests |
| 7 | `stage-3.1-s3-upload-workflow` | validated presigned upload and checksum reservation | mocked AWS integration tests |
| 8 | `stage-3.2-async-processing` | S3-triggered processing/status/thumbnail persistence | event-handler integration tests |
| 9 | `stage-3.3-notifications` | SNS subscription filters and deduplicated watched-tag publish | notification tests |
| 10 | `stage-4.1-rest-api` | complete authenticated REST contract and errors | route/contract tests |
| 11 | `stage-4.2-cognito-iam` | Cognito/JWT configuration and least-privilege IAM | template assertions and auth tests |
| 12 | `stage-5.1-ui-auth` | React shell, register/login/logout/route guard/Google button | component tests |
| 13 | `stage-5.2-ui-upload-results` | upload, polling, results previews/original links | UI workflow tests |
| 14 | `stage-5.3-ui-queries` | all query modes including temporary file | UI query tests |
| 15 | `stage-5.4-ui-management` | bulk tags, delete, notifications, usability states | UI management tests |
| 16 | `stage-6.1-infrastructure` | SAM/container definitions, deploy scripts, cost guardrails | lint/template tests |
| 17 | `stage-6.2-integration-e2e` | local contract/E2E, security and failure regression | full automated suite |
| 18 | `stage-6.3-aws-deployment` | real AWS deployment and live E2E evidence | URLs, logs, screenshots, recorded blockers |
| 19 | `stage-7.1-final-handoff` | final docs, demo, four-person handoff and HD audit | final checklist and clean repo |

## Stage procedure

For each stage:

1. verify the previous branch and working tree;
2. create the named branch from the passing stage;
3. implement only the current bounded scope;
4. run relevant unit, integration, and regression tests;
5. write `STAGE_X_REPORT.md` and `STAGE_X_HANDOFF.md`;
6. inspect staged files for secrets and generated artifacts;
7. commit with a meaningful message and push the branch;
8. proceed immediately to the next stage.

## Principal risks and mitigations

| Risk | Mitigation |
|---|---|
| PyTorch/MegaDetector dependency conflict | pin a tested Python 3.12 stack; separate runtime and development dependencies |
| 493 MB model weights and Lambda package limits | Git LFS for source history; ML Lambda container and versioned model configuration |
| ML Lambda cold start/cost | lazy singleton models, API/upload throttles, short videos, demo-sized workload |
| duplicate uploads racing | DynamoDB conditional checksum reservation with TTL |
| uploaded checksum is dishonest | recompute SHA-256 in processor and fail safely on mismatch |
| public data exposure | private S3, JWT authorizer, least privilege, expiring presigned URLs |
| presigned thumbnail URL changes | persist object key and parse/normalize incoming URL before lookup |
| frame-level double counting | define video count as the maximum simultaneous count per species across sampled frames; document it |
| temporary query file retained after failure | `finally` deletion plus S3 one-day lifecycle fallback |
| temporary ML exceeds HTTP API timeout | S3/EventBridge orchestration plus owner-scoped TTL status polling |
| SNS pending confirmation | expose status and clear user guidance; do not report success until confirmed |
| AWS Free Plan depletion | cost guardrails above; no upgrade; stop before paid/high-risk actions |
| AWS-only versus PDF language | retain instructor's written clarification and cite it in the final report |
| superficial member commits | require each member to run, test, explain, and materially review/modify assigned code |

## Final acceptance criteria

The Prototype is complete only when all items in the TXT completion checklist
have objective evidence, the full test suite passes, live AWS results are not
simulated, no secret is present, all stage branches exist remotely, and each
Rubric row has a recorded demonstration path.
