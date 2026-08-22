# Stage 6.3 Handoff — AWS Deployment and Live Acceptance

## Ownership

This stage owns the transition from the portable Stage 6.2 system to an
observed AWS deployment. It covers GitHub OIDC/ECR publication, CloudFormation
quota remediation, same-name stack deployment, private SPA delivery, live
security/cost acceptance and the complete browser demonstration.

The stage is still in progress while the AWS sign-in and live acceptance gates
remain pending. Do not present it as completed from local tests alone.

## Key files

- `infrastructure/template.yaml` — Sydney-only serverless root stack.
- `infrastructure/github-oidc-bootstrap.yaml` — retained ECR and tightly scoped
  GitHub OIDC trust.
- `infrastructure/scripts/deploy-core.sh` — guarded, immutable-digest SAM
  deployment.
- `infrastructure/scripts/deploy-frontend.sh` — guarded private-S3/CloudFront
  SPA build and sync.
- `infrastructure/scripts/verify-live-stack.sh` — read-only, sanitized live
  acceptance gate.
- `backend/tests/unit/test_infrastructure_template.py` — quota, security,
  immutable-image and live-script regression assertions.
- `docs/DEPLOYMENT_GUIDE.md`, `docs/DEMO_PLAN.md` and `docs/USER_GUIDE.md` —
  operator and demonstration flow.

## Required operator sequence

1. Confirm the browser is authenticated to account `835597620771` in Sydney
   and Billing/Free Plan still reports US$0 with available free allowance.
2. Confirm the old root stack is exactly `ROLLBACK_COMPLETE`; delete that stack
   record only. Retained media/model/Cognito resources require deliberate
   review and must not be broadly deleted.
3. Reuse stack name `pacific-bioarchive-prototype` and the recorded immutable
   ECR digest. Review the generated change set before execution.
4. Wait for `CREATE_COMPLETE`, deploy the SPA, then run:

   ```bash
   bash -n infrastructure/scripts/verify-live-stack.sh
   bash infrastructure/scripts/verify-live-stack.sh \
     | tee docs/evidence/LIVE_STACK_ACCEPTANCE.txt
   ```

5. Use the deployed UI for the full `docs/DEMO_PLAN.md` sequence. Cognito email
   verification and SNS email confirmation require a human recipient.
6. Remove live demo media through the application and verify the corresponding
   objects, records and deduplication state are gone. Retained infrastructure
   cleanup is a separate, explicitly authorized task.

## What the member must understand

- Why an ECR `@sha256` URI is safer and more reproducible than `:latest`.
- Why OIDC removes stored GitHub AWS keys and how repository/branch/audience
  conditions restrict assumption.
- Why the Academy account needs 3008 MB and no reserved concurrency even though
  the original template validated locally.
- How the default JWT authorizer protects every business route, including
  `/health`, and why an unauthenticated 401 is part of the acceptance gate.
- How private S3, CloudFront OAC, least-privilege roles, seven-day logs,
  PAY_PER_REQUEST tables and no NAT/EC2/RDS choices control cost and exposure.

## Validation

Local:

```powershell
./infrastructure/scripts/validate.ps1
```

Live, after `CREATE_COMPLETE`:

```bash
bash infrastructure/scripts/verify-live-stack.sh
```

Latest local result is 112 backend tests, 90.12% domain/application coverage,
20 frontend tests and all lint/build/template gates passing. This is not a
substitute for the pending live run.

## Likely demonstration questions

- Show that an anonymous browser and a direct unauthenticated API request are
  blocked.
- Explain checksum deduplication and why filename matching is insufficient.
- Show 1 frame/second video aggregation and where the supplied ML models run.
- Demonstrate AND minimum-count queries, thumbnail recovery and temporary-file
  cleanup.
- Explain complete deletion, notification deduplication and the SNS pending
  state.
- Identify which AWS resources could cost money and the controls that bound
  them.

## Secrets and evidence

Never copy tokens, credentials, email codes, OAuth values, pre-signed URLs or
unredacted user data into Git, screenshots, terminal transcripts or chat. The
acceptance script intentionally emits only pass/fail labels. Any screenshots
must be reviewed and cropped/redacted before they become assessment evidence.

