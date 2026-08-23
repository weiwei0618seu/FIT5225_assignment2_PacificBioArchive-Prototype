# HD Rubric Audit

Status legend: **PASS** = observed evidence; **READY** = implementation and
automated evidence exist but live AWS/human confirmation is still required;
**OPTIONAL** = enhancement beyond the stable core.

| Rubric item | Status | Evidence / remaining live gate |
|---|---|---|
| 1.1 Cognito sign-up/sign-in/sign-out | READY | Native flows, all required fields and tests; verify real Cognito email/session. |
| 1.2 block/redirect unauthenticated | READY | Protected React routes, JWT authorizer/IAM tests; probe deployed page and API. |
| 1.3 fine-grained IAM | READY | Separate exact-resource roles, private S3, OIDC-bound ECR publisher; inspect live policies. |
| 2.1.1 upload/checksum dedup | PASS/READY | Unit/integration pass; demonstrate exact-byte duplicate in AWS. |
| 2.1.2 thumbnail/video 1 fps | PASS/READY | Aspect/compression and sampling tests; verify stored thumbnail/short live video. |
| 2.1.3 ML tagging/DB insertion | PASS/READY | Real local/Linux/ECR image proof; execute real Lambda and inspect DynamoDB. |
| 2.2.1 tag/count/species AND | PASS/READY | Boundary/AND tests and UI; run against live records. |
| 2.2.2 thumbnail to original | PASS/READY | URL normalization tests/UI; live expiring URL lookup. |
| 2.2.3 query by uploaded file | PASS/READY | Success/failure cleanup and cross-user tests; prove live temp key removed. |
| 2.3.1 bulk tag edit | PASS/READY | Multi-item add/remove/absent-delete tests/UI; live owner update. |
| 2.3.2 bulk complete delete | PASS/READY | Object/record/dedup/idempotency tests/UI confirmation; live outcomes. |
| 2.3.3 watched-tag email | READY | SNS filter/dedup implementation/tests; human email confirmation and delivery. |
| 3.1 auth/upload UI | PASS/READY | React tests/build and explicit loading/success/duplicate/error states; deploy screenshot. |
| 3.2 queries UI | PASS/READY | Four modes, thumbnails/original links and empty states; live walkthrough. |
| 3.3 bulk/usability UI | PASS/READY | Bulk selection, edit, destructive confirmation, outcomes; live walkthrough. |
| 3.4 external account | OPTIONAL | Cognito code-flow/PKCE path exists; needs team-owned Google OAuth credentials and live record. |
| 4.1 demo | READY | `DEMO_PLAN.md`, fixtures, member ownership/Q&A; full rehearsal required. |
| 4.2 Team Report | READY | Source docs/user guide/handoff exist; names/IDs and official-icon PDF still human-owned. |
| 4.2 Individual Reports | READY | Each student must independently write/submit their own report. |
| GenAI declaration | PASS/READY | `GENAI_USAGE.md` maintained; must also appear in both submitted report types. |

## Current measured gate

- backend: 114 passed (plus one Windows-only Bash availability skip);
  domain/application coverage 90.12%; Ruff pass;
- frontend: 20 passed; TypeScript, Vitest, build and ESLint pass;
- CloudFormation: cfn-lint pass; infrastructure security assertions pass;
- real supplied model: three expected fixtures pass locally and in Linux;
- immutable ECR publish: workflow run `32601871666`, job `97101257587`,
  immutable digest `sha256:1d67986a6dff37ba8a71830d84847b35e91e86bb6b1fe9a83e913a9ba2f7cef3`,
  successful;
- live root stack/UI/E2E: pending completion and honest Stage 6.3 evidence.

The project should not be called finally complete while any READY item required
for the core demo lacks observed live evidence. Google login may remain clearly
documented as optional if credentials are unavailable.
