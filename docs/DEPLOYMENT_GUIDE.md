# Deployment Guide

This guide deploys the Prototype to one AWS account in `ap-southeast-2`. The
teaching team's written AWS-only clarification supersedes the older multi-cloud
wording in the assignment PDF.

## Cost and safety gate

Before every deploy, confirm the AWS console still shows the Free Plan/expected
credits and no unexpected spend. Do not upgrade the plan. The template creates
no EC2, NAT Gateway, RDS, OpenSearch, SageMaker, EFS or WAF. DynamoDB is
on-demand, logs expire after seven days, temporary query objects expire after
one day, and API traffic is throttled. The optional budget resource is disabled
by default because Academy roles may reject it.

S3 media/model buckets and the Cognito user pool use `DeletionPolicy: Retain`.
They survive stack rollback/deletion and must be cleaned up deliberately after
assessment. Do not run cleanup commands during a demo.

## Prerequisites

- AWS console/CloudShell authenticated to account `835597620771`;
- region `ap-southeast-2`;
- AWS CLI, SAM CLI, Docker, Node.js, npm and `jq` in CloudShell;
- repository source without `.env`, secrets or unnecessary model duplicates;
- successful local `infrastructure/scripts/validate.ps1`;
- immutable ECR image evidence, never a mutable tag.

The verified Stage 6.3 image is:

```text
835597620771.dkr.ecr.ap-southeast-2.amazonaws.com/pacific-bioarchive-prototype-ml@sha256:1d67986a6dff37ba8a71830d84847b35e91e86bb6b1fe9a83e913a9ba2f7cef3
```

## 1. Validate locally

```powershell
./infrastructure/scripts/validate.ps1
```

Expected gate: backend tests and >=85% domain/application coverage, Ruff,
frontend typecheck/tests/build/ESLint, cfn-lint, and SAM validation when SAM is
installed.

## 2. Bootstrap secret-free GitHub publishing

In CloudShell:

```bash
PBA_CONFIRM_FREE_PLAN='US$0' bash infrastructure/scripts/bootstrap-ecr.sh
```

Review the change set before accepting it. The OIDC trust is limited to the
immutable private-repository owner/repository IDs and
`stage-6.3-aws-deployment`. It grants push access only to the single ML ECR
repository. No AWS access key is stored in GitHub.

Run the `Publish verified ML image` workflow and record its run ID, commit,
digest, image size, model predictions and artifact checksum. Stage 6.3 uses
successful run `32601871666`, job `97101257587`, for commit
`b42dc43c65031aa0e5b2d2175a2467f0cda60b0d`.

## 3. Deploy the core stack

Choose a globally unique lowercase Cognito prefix. The current Prototype uses
`pba-prototype-835597620771`.

```bash
export PBA_CONFIRM_FREE_PLAN='US$0'
export PBA_HOSTED_UI_DOMAIN_PREFIX='pba-prototype-835597620771'
export PBA_ML_IMAGE_URI='835597620771.dkr.ecr.ap-southeast-2.amazonaws.com/pacific-bioarchive-prototype-ml@sha256:1d67986a6dff37ba8a71830d84847b35e91e86bb6b1fe9a83e913a9ba2f7cef3'
bash infrastructure/scripts/deploy-core.sh
```

The script validates, builds with the official Lambda Python 3.12 SAM container
and pauses at the CloudFormation change set. This avoids incorrectly resolving
the Python ZIP dependencies against CloudShell's Python 3.13 host runtime. The
first invocation may pull that official build image through Docker.
Reject it if it contains a resource outside the documented architecture.
Academy accounts may expose only the minimum Lambda unreserved concurrency, so
the template deliberately omits `ReservedConcurrentExecutions`; cost is bounded
with API/upload limits, short videos and timeouts instead.

### CloudShell low-disk fallback and change-set-only mode

The current CloudShell host may not have enough ephemeral root-disk space to
unpack the official SAM build image. In that case, do not fall back to a host
Python 3.13 build. Run the repository's pinned
`Verify deployment build toolchain` GitHub workflow, download its
`sam-python312-build-<run-id>` artifact and upload the two contained files to
CloudShell. The workflow has already pulled and run the official Python 3.12
image and created the archive with `sam build --use-container`.

Prepare a change set without executing it:

```bash
export PBA_CONFIRM_FREE_PLAN='US$0'
export PBA_HOSTED_UI_DOMAIN_PREFIX='pba-prototype-835597620771'
export PBA_ML_IMAGE_URI='835597620771.dkr.ecr.ap-southeast-2.amazonaws.com/pacific-bioarchive-prototype-ml@sha256:1d67986a6dff37ba8a71830d84847b35e91e86bb6b1fe9a83e913a9ba2f7cef3'
export PBA_PREBUILT_SAM_ARCHIVE="$HOME/sam-python312-build.tar.gz"
export PBA_PREBUILT_SAM_SHA256="$(cut -d ' ' -f 1 "$HOME/sam-python312-build.tar.gz.sha256")"
export PBA_DEPLOY_MODE='prepare'
bash infrastructure/scripts/deploy-core.sh
```

The script requires a 64-character SHA-256 match, rejects archive members
outside `build/`, extracts to a short-lived directory and passes
`--no-execute-changeset`. Review the exact proposed resources before running
the selected change set:

```bash
AWS_PAGER='' aws cloudformation list-change-sets \
  --stack-name pacific-bioarchive-prototype \
  --region ap-southeast-2

AWS_PAGER='' aws cloudformation describe-change-set \
  --stack-name pacific-bioarchive-prototype \
  --change-set-name '<reviewed-change-set-name>' \
  --region ap-southeast-2

aws cloudformation execute-change-set \
  --stack-name pacific-bioarchive-prototype \
  --change-set-name '<reviewed-change-set-name>' \
  --region ap-southeast-2
```

Never execute a change set merely because it was generated successfully.
Confirm the account, region, immutable image digest and resource types first.

After completion, capture outputs without secrets:

```bash
AWS_PAGER='' aws cloudformation describe-stacks \
  --stack-name pacific-bioarchive-prototype \
  --query 'Stacks[0].{Status:StackStatus,Outputs:Outputs}' --output json
```

## 4. Deploy the SPA

```bash
PBA_CONFIRM_FREE_PLAN='US$0' bash infrastructure/scripts/deploy-frontend.sh
```

The script reads stack outputs, creates ignored
`frontend/.env.production.local`, builds the SPA, syncs it to the private
frontend bucket, and invalidates CloudFront. Public identifiers in the generated
file are not credentials; never add Cognito passwords/tokens or OAuth secrets.

pnpm `11.19.0` requires Node.js 22.13 or newer. If the deployment host exposes
an older Node.js, build `frontend/dist` on a compatible host after generating
the production environment file, ZIP the contents of `dist` at the archive
root, upload the ZIP and deploy it through the authenticated fallback:

```bash
export PBA_PREBUILT_FRONTEND_ARCHIVE=/home/cloudshell-user/pba-frontend.zip
export PBA_PREBUILT_FRONTEND_SHA256='<observed-64-character-sha256>'
PBA_CONFIRM_FREE_PLAN='US$0' bash infrastructure/scripts/deploy-frontend.sh
```

The fallback validates the SHA-256, ZIP integrity and member boundaries before
syncing. It never treats an incompatible Node runtime as a successful build.

## 5. Verify native Cognito and SNS

1. Open `FrontendUrl` in Chrome.
2. Register with email, first name, last name and a strong password.
3. Enter the Cognito email code and sign in.
4. In Manage, watch a tag and confirm the SNS email before expecting delivery.
5. Upload a matching fixture and verify exactly one notification event.

Email-code and SNS confirmation links are human account actions and must not be
automated or recorded as successful until completed.

## 6. Optional external Google authentication

Google login is an enhancement after the native flow is stable. Create a Google
OAuth Web Application using the exact `GoogleOAuthRedirectUrl` output, then
update CloudFormation with `EnableGoogleFederation=true` and transient `NoEcho`
client ID/secret values. Never place these values in Git, terminal history,
screenshots, chat, `.env` or `samconfig.toml`.

If credentials are unavailable, leave federation disabled and state that the
core Cognito requirement is complete while rubric item 3.4 remains unclaimed.

## 7. Live smoke checklist

- unauthenticated page/API access rejected;
- registration, verification, sign-in and sign-out;
- image upload, processing, thumbnail and expected real-model tag;
- same bytes under another filename rejected as duplicate;
- video samples one frame per second;
- species, strict count/AND, thumbnail and temporary-image queries;
- temporary object absent after success and forced failure;
- bulk add/remove tag, including removal of an absent tag;
- original/thumbnail/metadata/checksum deletion and idempotent retry;
- confirmed watched-tag SNS email;
- CloudWatch logs contain request IDs but no tokens or credentials.

Record commands, UTC timestamps, resource IDs and sanitized responses under
`docs/evidence/`; never invent evidence or commit JWTs/presigned URLs.
