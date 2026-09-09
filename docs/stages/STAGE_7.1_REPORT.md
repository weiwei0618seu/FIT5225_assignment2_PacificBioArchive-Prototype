# Stage 7.1 Report — Final Technical Handoff

## Status and boundary

**Technical implementation and evidence handoff complete.** The Prototype
repository contains the tested application, deployed AWS architecture,
sanitized live evidence, operator/user/demo guidance, four-member ownership
plan and a visually verified Team Report draft.

This stage does not claim that the university submission pack is complete. The
four member names, student IDs and truthful contribution percentages are facts
that the students must supply and confirm. The final Team Report PDF must only
be exported after those values are inserted. No member may exceed the
assignment's 30% contribution limit.

Only
`weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype` was modified.
The formal Group 8 repository was not changed.

## Final delivered state

- The Sydney root stack is `UPDATE_COMPLETE`; the private CloudFront SPA and
  Cognito-protected API are live.
- The supplied detector/classifier is reused without retraining in immutable
  Lambda image digest
  `sha256:c51c7685bbafcff84baa42e2c5622f7d4503c731b43f2b9a4f7a3ee0ef755e31`.
- Live acceptance covers native registration/verification/sign-in, protected
  routing, image and three-frame video processing, thumbnail generation,
  checksum deduplication, all four query modes, asynchronous temporary-query
  success/failure cleanup, idempotent bulk tag/delete behavior, confirmed SNS
  watched-tag delivery, logout protection and CloudWatch sensitive-field
  checks.
- `docs/evidence/LIVE_E2E.json` records 22 required checks as `PASS` and three
  human confirmations. Its SHA-256 is
  `27F6E6B040BC070E73EDF28766DD1F6DDDCFA93057F8ED5B3A6C13F2C61DFEB5`.
- `docs/evidence/LIVE_STACK_ACCEPTANCE.txt` records all ten sanitized live
  infrastructure checks. Its SHA-256 is
  `FCACC4E2A94A759CF6B6646C8E2F3A7FDBE020541B5D0898684B34AF33A918B9`.
- The AWS design remains bounded and serverless: private encrypted S3,
  on-demand encrypted DynamoDB, bounded Lambda, seven-day logs, API throttling
  and no EC2, NAT Gateway, RDS, OpenSearch, SageMaker, EFS or WAF resources.
- The checked monthly cost was effectively US$0. Free-plan monitoring and
  deliberate teardown remain operator responsibilities; no broad retained
  resource deletion was authorized or performed.

## Measured final gates

Observed on 2026-09-09:

| Gate | Result |
|---|---|
| Backend tests | 121 passed; one Windows-only Bash availability skip |
| Domain/application coverage | 89.39%, above the 85% enforced minimum |
| Frontend | 23 tests, TypeScript, production build and ESLint passed |
| Backend/infrastructure quality | Ruff, cfn-lint and template assertions passed |
| Supplied model | Three hash-bound fixtures passed locally and in Linux |
| Live stack evidence | Ten sanitized checks passed |
| Live E2E evidence | 22 required checks and three human confirmations passed |
| Delivery audit | Seven repository/document/model/security checks passed |
| Strict final-submission audit | Correctly stopped at the absent genuine final PDF |
| Git whitespace audit | `git diff --check` passed |

`infrastructure/scripts/validate.ps1` was rerun after the final evidence and
report updates. The Windows host has no local SAM CLI or Bash, so cfn-lint and
the template unit tests covered CloudFormation locally; the matching official
SAM Python 3.12 container build and Bash live verifier had already passed in
Linux/AWS evidence.

## Team Report quality gate

`docs/report/Pacific_BioArchive_Team_Report_DRAFT.docx` is a five-page,
778-word Arial 12 pt draft with official AWS icons, a contribution table,
concise user guide, explicit Generative AI declaration and two sanitized live
UI figures. Its SHA-256 is
`8B70FD70C2941FC8D1E73EA6F2E136BC68E2B33843A8A83F864557E530262D60`.

Microsoft Word PDF export was rendered to five page images and every page was
visually inspected. No clipping, overlap, split rows, broken page furniture or
unreadable labels were observed. The accessibility audit returned zero
high/medium/low findings; the image audit found three inline images and no
floating anchors; the contribution table has exact 9360 DXA geometry with a
120 DXA indent and matching cell widths.

The final PDF is intentionally absent because exporting the placeholder member
identities and provisional contribution split as a final report would be
misleading. This is the only Team Report publication gate.

## Security and evidence hygiene

- No password, verification code, JWT, AWS credential, signed URL, email
  address, Cognito subject or private media identifier was committed in the
  live E2E record or screenshots.
- The thumbnail reference and remembered sign-in values are covered by opaque
  redactions in the committed evidence.
- The user-provided SNS confirmation screenshot was not committed because it
  contained an account identifier and ARN.
- The delivery audit found no credential pattern or non-portable runtime path
  in tracked text and both Git LFS model objects passed `git lfs fsck`.

## Human-owned completion actions

1. Confirm all four names and student IDs.
2. Confirm truthful contribution percentages and descriptions, with each
   percentage at or below 30%.
3. Replace the placeholders in the verified DOCX and repeat its render,
   accessibility, image, table-geometry, word-count and hash checks.
4. Export and commit
   `docs/report/Pacific_BioArchive_Team_Report_FINAL.pdf`.
5. Integrate the understood member-owned deltas into the formal private Group 8
   repository using each student's own GitHub account.
6. Rehearse the complete demo and prepare each independently written Individual
   Report.
7. Push a clean final handoff branch and run
   `./scripts/verify-final-delivery.ps1 -RequireFinalState`.

Until those human-owned actions are complete, the ordinary delivery audit is
the truthful technical gate; strict final-submission mode is expected to reject
the missing final PDF. The strict gate was exercised in this stage and rejected
exactly `docs/report/Pacific_BioArchive_Team_Report_FINAL.pdf`, with all seven
preceding technical checks passing.
