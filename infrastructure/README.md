# Pacific BioArchive infrastructure

`template.yaml` is the root SAM template. It packages the local
`auth-and-iam.json` application and lightweight API ZIP, then binds two Lambda
commands to one immutable Sydney ECR image digest. `github-oidc-bootstrap.yaml`
creates the single retained ECR repository and a branch-bound GitHub OIDC push
role; it does not create long-lived AWS access keys.

## Safety boundary

- The template contains a rule that rejects every region except
  `ap-southeast-2`.
- It uses no EC2, NAT Gateway, RDS, OpenSearch, SageMaker, EFS or WAF.
- DynamoDB is on-demand; Lambda concurrency is 2/1/1; logs expire after seven
  days; API request rates are throttled; query objects expire after one day.
- All three S3 buckets block public access and use HTTPS-only bucket policies.
- CloudFront reads the private SPA bucket through SigV4 OAC.
- A US$1 budget with a US$0.10 alert is available but disabled by default
  because some student/lab roles cannot create Budgets resources.
- Buckets containing media/models and the Cognito user pool are retained to
  prevent accidental assessment-data loss. They require deliberate cleanup.

These controls reduce risk but do not guarantee zero spend. Before deployment,
inspect AWS Billing/Free Plan in the signed-in account and review the generated
CloudFormation change set. Never upgrade the account or add paid services.

## Validation

```powershell
./infrastructure/scripts/validate.ps1
```

Docker is required only in GitHub Actions to build and smoke the real ML image.
The SAM deploy consumes the resulting `@sha256` ECR URI, so AWS CloudShell needs
the AWS CLI and SAM CLI but no Docker. Stage 6.2 records the successful portable
container proof; Stage 6.3 must separately record ECR and live Lambda evidence.

## Deployment sequence

1. Run all validation and the real Linux model smoke test.
2. Confirm Billing/Free Plan is US$0, credits remain, the account remains on
   Free Plan and the region is `ap-southeast-2`.
3. In AWS CloudShell, upload this repository without model weights and run
   `PBA_CONFIRM_FREE_PLAN='US$0' bash infrastructure/scripts/bootstrap-ecr.sh`.
4. Verify the branch-bound `publish-ml-image.yml` run. Its non-secret role ARN
   and repository URI are fixed to the observed bootstrap outputs because the
   repository's baseline default branch cannot expose this later workflow for
   manual dispatch. Record the successful run and immutable `image_uri`; never
   use a mutable tag in SAM.
5. In CloudShell, set `PBA_HOSTED_UI_DOMAIN_PREFIX`, `PBA_ML_IMAGE_URI` and
   `PBA_CONFIRM_FREE_PLAN='US$0'`, then run
   `bash infrastructure/scripts/deploy-core.sh`. Review the printed
   CloudFormation change set before answering its confirmation prompt.
   Windows operators can instead use `deploy-core.ps1` with the same digest.
6. Deploy the SPA from CloudShell with
   `PBA_CONFIRM_FREE_PLAN='US$0' bash infrastructure/scripts/deploy-frontend.sh`,
   or use `deploy-frontend.ps1` on Windows.
7. Create the Google OAuth Web Application with the exact
   `GoogleOAuthRedirectUrl` output.
8. Update the root stack through CloudFormation using transient `NoEcho`
   `GoogleClientId`/`GoogleClientSecret` values and
   `EnableGoogleFederation=true`. Do not put those values in Git, terminal
   history, `samconfig.toml`, screenshots or chat.
9. Confirm one Cognito verification email and one SNS subscription email, then
   run the live E2E checklist.

Both deployment scripts require an explicit confirmation switch. The core
script intentionally cannot accept Google secrets.
