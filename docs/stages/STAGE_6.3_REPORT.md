# Stage 6.3 Report — AWS Deployment and Live Acceptance

## Status and objective

**Complete — deployed core and complete authenticated workflow accepted.**
The real Sydney stack and private SPA are live, the read-only infrastructure
acceptance gate passes, and real image/video ML, strict-AND search, bulk tag
editing, complete idempotent deletion and asynchronous temporary-image query
workflows have been observed. The recipient observed the watched-tag email,
logout completed, and a direct protected-route revisit returned to sign-in.

The deployment remains restricted to the Prototype repository and
`ap-southeast-2`. It does not modify the formal Group 8 submission repository.

## Observed work completed so far

- Published the real ML container through GitHub OIDC without long-lived AWS
  credentials. Workflow run `32601871666`, job `97101257587`, succeeded for
  commit `b42dc43c65031aa0e5b2d2175a2467f0cda60b0d`.
- Bound both ML Lambdas to immutable ECR digest
  `sha256:1d67986a6dff37ba8a71830d84847b35e91e86bb6b1fe9a83e913a9ba2f7cef3`.
- Restricted OIDC trust to the private repository's immutable owner/repository
  IDs, the Stage 6.3 branch and `sts.amazonaws.com` audience.
- Observed and retained two honest failed root-stack deployments:
  1. the Academy account rejected the original 4096 MB Lambda setting because
     its exposed maximum was 3008 MB;
  2. after reducing memory, Lambda reserved concurrency would have left fewer
     than the account-required ten unreserved executions.
- Fixed those quota incompatibilities by using 3008 MB for ML functions and
  omitting reserved concurrency from all three functions. Local template and
  regression gates pass after both changes.
- Kept the Lambda ZIP runtime at Python 3.12 and changed both deployment paths
  to fail closed without Docker and use `sam build --use-container`. This
  supplies the matching official build runtime even though the current
  CloudShell host provides Python 3.13.
- Verified the complete deployment toolchain in GitHub Actions run
  `32610702537`, job `97123189935`, for commit `410b65c61f70059956faa181a496f5e1126e83f7`.
  The run succeeded after pulling and running
  `public.ecr.aws/sam/build-python3.12:latest-x86_64`, asserting Python 3.12,
  completing `sam build --use-container`, asserting pnpm `11.19.0`, installing
  the frozen frontend lockfile and completing the production build.
- Deleted the same-name `ROLLBACK_COMPLETE` stack record only after that gate
  passed. The CloudFormation delete waiter returned zero and a subsequent
  `describe-stacks` returned the expected not-found response.
- Added a SHA-256 authenticated portable SAM build path for CloudShell. This is
  required because the official build image exhausted the host's ephemeral
  root disk while unpacking; the cancelled pull released all temporary Docker
  layers and left no images, containers, volumes or build cache.
- Added `infrastructure/scripts/verify-live-stack.sh`, a read-only acceptance
  gate that suppresses raw AWS responses and checks:
  - root stack `CREATE_COMPLETE`;
  - active Lambda state, bounded memory, no reserved concurrency and resolved
    immutable ECR digest;
  - S3 public-access blocks, encryption and TLS-only policies;
  - active, encrypted, on-demand DynamoDB tables;
  - the exact business-route set with JWT authorization and unauthenticated
    `/health` returning HTTP 401;
  - enabled/deployed CloudFront and seven-day log retention;
  - absence of EC2, NAT, RDS, OpenSearch, SageMaker, EFS and WAF resources from
    root and nested stacks.
- Downloaded workflow run `32610952406` artifact `9485516997`, verified outer
  ZIP SHA-256 `6d4b1862f8d0ac3da1077e031391f911129546ebdbe3a7d6a74420fa25d63adb`
  and inner SAM archive SHA-256
  `e67a36d61ff66a2482f800e14628ac54e1e9040a5ea61ae8d7e5b170986d7056`.
- Prepared change set `samcli-deploy1787450298` and stopped before execution.
  The automated safety gate re-read it and proved the correct account/region,
  `REVIEW_IN_PROGRESS`, `CREATE_COMPLETE/AVAILABLE`, 39 Add-only changes,
  zero excluded services, a present ECR digest, an available Cognito domain,
  and disabled Google federation/cost budget parameters.
- Executed that reviewed change set. The same-name root stack reached
  `CREATE_COMPLETE` with no failed or rollback event.
- Built the configured SPA with local Node.js 24 and pnpm `11.19.0` after
  CloudShell's Node.js 20 correctly rejected pnpm 11. The authenticated archive
  was uploaded to the new empty private frontend bucket and both CloudFront
  invalidations completed.
- Corrected the live acceptance script for the AWS CLI's successful empty
  `get-function-concurrency` response, then observed all ten sanitized PASS
  labels in `docs/evidence/LIVE_STACK_ACCEPTANCE.txt`.
- Observed CloudFront redirect to native sign-in, the complete registration
  form and an empty browser error log. Disabled Google federation is now hidden
  instead of exposing an unusable button; the live page was rebuilt, published
  and rechecked.
- Registered and verified a native Cognito user, signed in through the deployed
  SPA and retained only sanitized/cropped evidence without the Cognito subject,
  email address, token, signed URL or private file identifier.
- Uploaded the supplied Australian brushturkey fixture and a three-second video.
  Both reached `READY`; the image rendered its generated thumbnail and the
  video recorded three one-frame-per-second samples using model `supplied-v1`.
- Added the manual `reviewed` tag to both records in one bulk operation. A live
  strict-AND query for `australian brushturkey >= 1` and `reviewed >= 1`
  returned exactly the image and video.
- Removed `reviewed` from both records in one bulk operation and repeated the
  same removal; the retry reported zero tag changes. After explicit destructive
  approval, permanently deleted both records and repeated the same request;
  the first outcomes were `Deleted` and the retry outcomes were
  `Already absent`. A sanitized AWS check found zero matching S3 objects,
  DynamoDB media records and checksum reservations.
- Observed the SNS email subscription transition to `CONFIRMED`, uploaded one
  supplied watched-tag fixture, and observed it reach `READY`. Sanitized AWS
  checks found one confirmed email subscriber and the upload's durable
  notification-event claim. Inbox delivery was reported as PASS only after the
  recipient confirmed receipt.
- Logged out only after all authenticated checks completed. A direct visit to
  the protected Manage route returned to the native sign-in page, and the
  evidence image covers remembered email/password fields with opaque labelled
  redactions.
- Replaced the synchronous temporary-image request with an asynchronous flow:
  S3 EventBridge delivery starts a narrowly scoped Python 3.12 orchestrator,
  which invokes the existing ML Lambda and writes a one-hour-TTL job result for
  frontend polling. The accepted stack update reached `UPDATE_COMPLETE` with
  no resource replacement.
- Observed a real temporary-image query transition from `PROCESSING` to `READY`,
  detected one Australian brushturkey and matched the existing image and video.
  The `query-temp/` prefix was empty after both successful live queries and the
  READY job records carried a one-hour TTL.
- Verified the temporary-job table uses on-demand capacity, server-side
  encryption and TTL; all three temporary-query routes remain JWT protected,
  and the new IAM permissions are limited to the job table and designated ML
  Lambda.
- Rebuilt the updated frontend with Node.js 22.19.0 and pnpm 11.19.0, uploaded
  without deleting unrelated bucket objects, and observed the CloudFront
  invalidation complete.
- Searched the four application log groups for the most recent hour and found
  no email address, JWT, `Authorization` header, signed-request field or
  Cognito subject value.
- Updated the Team Report draft to the deployed asynchronous architecture and
  measured 121/23-test evidence, replacing both UI placeholders with sanitized
  live upload and strict-AND figures. Microsoft Word reports 778 words across
  five pages; all pages were visually reviewed, the accessibility audit found
  no findings, and table geometry remained exact. Final live outcomes are included;
  only member identities/contributions and final PDF export remain human-owned.

## Deployment attempts and remediation

| Attempt | Observed result | Remediation |
|---|---|---|
| Root stack 1 | Rollback: requested 4096 MB exceeded the account's 3008 MB limit | Reduced both ML functions to 3008 MB and added regression assertions |
| Root stack 2 | Rollback: reserved concurrency violated the account's minimum unreserved pool of 10 | Removed all `ReservedConcurrentExecutions` settings and added regression assertions |
| Root stack 3 | `CREATE_COMPLETE`; reviewed 39 Add-only changes, no failed/rollback event | Retain as the accepted live prototype and continue authenticated E2E evidence |

No second root-stack name will be created. Media/model buckets and Cognito data
covered by retention policies must remain intact across the retry.

## Measured local/CI gate

Command:

```powershell
./infrastructure/scripts/validate.ps1
```

Latest result on 2026-08-23:

- backend: 121 passed, 1 Bash-availability skip on Windows;
- domain/application coverage: 89.39% (minimum 85%);
- frontend: 23 passed;
- TypeScript, production build, ESLint and Ruff: passed;
- cfn-lint and infrastructure assertions: passed.

The skipped test asks a locally installed Bash to parse the acceptance script.
Windows has no Bash runtime; `bash -n` and the complete script both passed in
AWS CloudShell.

## Live acceptance record

| Gate | Status | Evidence location |
|---|---|---|
| Same-name root stack retry | PASS | `docs/evidence/LIVE_STACK_ACCEPTANCE.txt` |
| Read-only stack acceptance | PASS (10 labels) | `docs/evidence/LIVE_STACK_ACCEPTANCE.txt` |
| Frontend deployment and anonymous UI | PASS | `docs/evidence/live-ui/00-registration.png`, `01-login-protected.png` |
| Cognito register/verify/login | PASS | Live verified user and authenticated SPA session; sanitized evidence only |
| Logout and post-logout protection | PASS | Logout completed; direct Manage revisit returned to sign-in; sanitized `09-logout-protected.png` |
| Image/video, ML, thumbnail and DynamoDB | PASS | Both records reached `READY`; image thumbnail and three video samples observed |
| Exact-byte duplicate rejection | PASS | `docs/evidence/live-ui/05-duplicate-checksum-rejected.png` |
| Species and strict-AND queries | PASS | `docs/evidence/live-ui/03-strict-and-manual-tag.png` |
| Asynchronous temporary query and success cleanup | PASS | `docs/evidence/live-ui/04-temporary-query-async.png`; empty prefix and one-hour TTL verified |
| Thumbnail URL lookup | PASS | `docs/evidence/live-ui/06-thumbnail-to-original.png` (signed/private fields visibly redacted) |
| Temporary failure cleanup | PASS | `docs/evidence/live-ui/07-temporary-query-failure-cleanup.png`; zero S3 objects plus FAILED one-hour-TTL job observed |
| Bulk add tag | PASS | Two selected records updated and strict-AND result observed |
| Bulk remove/idempotency and complete deletion | PASS | Two removals plus zero-change retry; two `Deleted` outcomes plus two `Already absent` outcomes; no S3/media/dedup residue |
| CloudWatch sensitive-field redaction | PASS | Sanitized four-log-group scan produced no matches |
| SNS confirmation and watched-tag delivery | PASS | Manage shows `CONFIRMED`; watched-tag upload is `READY`; event claim and human inbox receipt observed |

## Cost and security boundary

- Deployment scripts require the explicit `PBA_CONFIRM_FREE_PLAN='US$0'`
  acknowledgement after inspecting Billing/Free Plan.
- `CreateCostBudget=false` avoids a Budgets permission/cost dependency in the
  Academy role; the architecture itself remains bounded and serverless.
- Do not enable Google federation without team-owned OAuth credentials. Native
  Cognito satisfies the core assignment flow; Google is an optional HD
  enhancement after the core live gate is stable.
- Evidence must contain no JWT, AWS credentials, email code, OAuth secret,
  pre-signed URL or private user data.

## Current controlled action

The user explicitly authorized the failed-stack-record deletion, official SAM
Python 3.12 build container and pnpm 11.19.0 execution. All three controls have
now been observed as complete. Cost Explorer reported
`-0.0000000001 USD` for the checked monthly period, effectively US$0.

CloudFormation retention left two Cognito user pools and four generated
media/model buckets from the two failed attempts. No retained resource was
deleted. The accepted root stack and frontend now exist alongside those
retained resources. Cognito registration, verification and sign-in are
complete. The SNS subscription is `CONFIRMED`, a watched-tag upload created its
notification-event claim, and the recipient observed the email. Logout and
post-logout protection pass. The separately authorized bulk tag removal,
permanent media deletion and both idempotency retries are complete.

## Completion criteria

1. Preserve only the sanitized evidence and rerun every gate.
2. Commit and push Stage 6.3, then create the final handoff stage.
