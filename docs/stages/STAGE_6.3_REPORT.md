# Stage 6.3 Report — AWS Deployment and Live Acceptance

## Status and objective

**In progress — deployed core accepted.** The real Sydney stack and private SPA
are live, and the read-only infrastructure acceptance gate passes. The stage
remains open only for authenticated media/ML workflows and the Cognito/SNS
email confirmations that require a student-controlled recipient.

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

- backend: 114 passed, 1 Bash-availability skip on Windows;
- domain/application coverage: 90.12% (minimum 85%);
- frontend: 22 passed;
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
| Cognito register/verify/login/logout | Pending human email step | Add sanitized UI screenshots |
| Image, video, duplicate, ML, thumbnail and DynamoDB | Pending | Add live E2E result |
| Four query modes and temporary cleanup | Pending | Add live E2E result |
| Bulk add/remove and complete deletion | Pending | Add live E2E result |
| SNS confirmation and watched-tag delivery | Pending human email step | Add sanitized result |

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
retained resources. The next action needs a student-controlled email address:
register and verify a Cognito user, sign in, confirm the SNS subscription and
run the complete image/video/query/manage/delete workflow.

## Completion criteria

1. Complete the full live UI/ML workflow, including Cognito and SNS human email
   confirmations.
2. Save only sanitized evidence, update this report and the HD rubric audit,
   rerun every gate, commit and push.
