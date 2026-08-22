# Stage 6.3 Report — AWS Deployment and Live Acceptance

## Status and objective

**In progress.** This stage owns the real Sydney deployment, private SPA,
authentication, supplied-model Lambda execution and live end-to-end evidence.
It is not complete until the root stack is `CREATE_COMPLETE`, the read-only
acceptance gate passes and the human-confirmation steps have been observed.

The deployment remains restricted to the Prototype repository and
`ap-southeast-2`. It does not modify the formal Group 8 submission repository.

## Observed work completed so far

- Published the real ML container through GitHub OIDC without long-lived AWS
  credentials. Workflow run `32597155253`, attempt 2, succeeded.
- Bound both ML Lambdas to immutable ECR digest
  `sha256:264e7840e9ae93cdb5e35afa30b33bdf4b9eb2965055d8f2bb8f90e8ad6e656b`.
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

## Deployment attempts and remediation

| Attempt | Observed result | Remediation |
|---|---|---|
| Root stack 1 | Rollback: requested 4096 MB exceeded the account's 3008 MB limit | Reduced both ML functions to 3008 MB and added regression assertions |
| Root stack 2 | Rollback: reserved concurrency violated the account's minimum unreserved pool of 10 | Removed all `ReservedConcurrentExecutions` settings and added regression assertions |
| Root stack 3 | Pending authenticated retry | Delete only the `ROLLBACK_COMPLETE` stack record, retain protected data resources, then deploy with the same stack name |

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
- frontend: 20 passed;
- TypeScript, production build, ESLint and Ruff: passed;
- cfn-lint and infrastructure assertions: passed.

The skipped test asks a locally installed Bash to parse the acceptance script.
Windows has no Bash runtime; Stage 6.3 must run `bash -n` and the live script in
AWS CloudShell before completion.

## Live acceptance record

This table deliberately remains pending until each result is observed in the
signed-in AWS account.

| Gate | Status | Evidence location |
|---|---|---|
| Same-name root stack retry | Pending | Add sanitized CloudFormation screenshot/transcript |
| Read-only stack acceptance | Pending | `docs/evidence/LIVE_STACK_ACCEPTANCE.txt` |
| Frontend deployment | Pending | Add private-S3/CloudFront evidence |
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

## Current blocker

The AWS console session expired and requires the user to complete IAM sign-in
and any MFA in the explicitly selected Chrome browser. This is a required human
account action under the project instructions, not a deployment or code claim.

## Completion criteria

1. Remove the existing `ROLLBACK_COMPLETE` root-stack record after confirming
   retained resources, then deploy the same stack name with the reviewed
   template and recorded immutable digest.
2. Deploy the frontend and run the read-only acceptance script in CloudShell.
3. Complete the full live UI/ML workflow, including Cognito and SNS human email
   confirmations.
4. Save only sanitized evidence, update this report and the HD rubric audit,
   rerun every gate, commit and push.
