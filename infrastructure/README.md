# Pacific BioArchive infrastructure

`template.yaml` is the root SAM template. It packages the local
`auth-and-iam.json` application, lightweight API ZIP and two commands from one
pinned ML container image.

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

The SAM CLI and Docker are additionally required to build the real ML image.
On this workstation those tools were not initially installed, so a successful
SAM/container build must not be claimed until Stage 6.2 records it.

## Deployment sequence

1. Run all validation and the real Linux model smoke test.
2. Confirm Billing/Free Plan is US$0 and the account remains on Free Plan.
3. Deploy the secret-free native-Cognito stack with `deploy-core.ps1`.
4. Deploy the SPA using stack outputs with `deploy-frontend.ps1`.
5. Create the Google OAuth Web Application with the exact
   `GoogleOAuthRedirectUrl` output.
6. Update the root stack through CloudFormation using transient `NoEcho`
   `GoogleClientId`/`GoogleClientSecret` values and
   `EnableGoogleFederation=true`. Do not put those values in Git, terminal
   history, `samconfig.toml`, screenshots or chat.
7. Confirm one Cognito verification email and one SNS subscription email, then
   run the live E2E checklist.

Both deployment scripts require an explicit confirmation switch. The core
script intentionally cannot accept Google secrets.
