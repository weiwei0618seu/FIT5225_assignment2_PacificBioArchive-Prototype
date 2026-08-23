# Stage 7.1 Handoff — Submission and Team Transfer

## Handoff outcome

The Prototype is technically complete and ready for four-member transfer. The
implementation, local/CI/live evidence and report source are preserved on
`stage-7.1-final-handoff`. Use this branch as the source of truth for the team
integration; do not modify or copy from another similarly named repository.

The formal Group 8 repository remains untouched by Codex. The students own its
integration history, report identities, contribution claims, Individual
Reports and final submission.

## Start here

1. Read `docs/HD_RUBRIC_AUDIT.md`, `docs/TEAM_HANDOFF_PLAN.md` and
   `docs/OFFICIAL_REPO_INTEGRATION_PLAN.md`.
2. Run the portable technical gate:

   ```powershell
   git lfs pull
   ./infrastructure/scripts/validate.ps1
   ./scripts/verify-live-e2e-evidence.ps1
   ./scripts/verify-final-delivery.ps1 -SkipValidation
   git status --short
   ```

3. Check that the model digest remains
   `sha256:1d67986a6dff37ba8a71830d84847b35e91e86bb6b1fe9a83e913a9ba2f7cef3`
   and that the Sydney stack is still `CREATE_COMPLETE` or `UPDATE_COMPLETE`.
4. Rehearse `docs/DEMO_PLAN.md` with all four members before making any live
   changes.

## Four-member transfer

Use `docs/TEAM_HANDOFF_PLAN.md` as the ownership map:

- Member 1: supplied ML, image/video processing and model evidence;
- Member 2: domain, persistence, queries and management API;
- Member 3: AWS eventing, SNS, infrastructure, OIDC/ECR and deployment;
- Member 4: Cognito, React UI, integration and final documentation.

Each member must understand, test and commit their own substantive delta to the
formal private repository from their own GitHub account. Do not manufacture
four-person contribution history from one account. Resolve interfaces against
the already integrated tree and run the full gate after each integration step.

## Team Report publication procedure

The current verified artifact is
`docs/report/Pacific_BioArchive_Team_Report_DRAFT.docx`; it is five pages and
778 words before the permitted exclusions. Preserve its structure and replace
only the four identity placeholders and any contribution fields the team
truthfully changes.

Before PDF export:

1. confirm every name and student ID exactly;
2. confirm the contribution percentages total 100% and no individual exceeds
   30%;
3. ensure every contribution description matches work that member can explain;
4. retain the private official repository link and Generative AI declaration;
5. rerender all pages and repeat accessibility, image and table-geometry audits;
6. save the reviewed submission as
   `docs/report/Pacific_BioArchive_Team_Report_FINAL.pdf`.

Do not rename the draft to `FINAL`, export a placeholder PDF or infer student
details. The strict delivery script intentionally fails when the genuine final
PDF is absent.

## Live AWS operating boundary

- Continue using `ap-southeast-2` and the current Free Plan/Academy account.
- Check Billing/Free Plan before deployment or a long live demonstration.
- Keep uploads short and within the documented limits; Lambda, S3, DynamoDB,
  SNS, ECR, CloudFront and CloudWatch can incur usage outside free allowances.
- Do not enable NAT Gateway, EC2, RDS, OpenSearch, SageMaker, EFS, WAF or an AWS
  Budget resource in the Academy role.
- Do not enable Google federation without team-owned OAuth credentials.
- Two failed deployment attempts retained Cognito/media/model resources. Do not
  broadly delete them; retained-resource cleanup requires a separate reviewed
  target list and explicit authorization.
- One watched-tag notification test media record remains from the final SNS
  delivery check. Delete it through the application only if the owner explicitly
  authorizes that separate destructive action, then verify S3, metadata and
  checksum cleanup.

## Evidence handling

Only commit sanitized evidence. Never retain passwords, email codes, JWTs, AWS
credentials, email addresses, Cognito subjects, ARNs from human confirmation
screens, signed URLs or private file identifiers. The committed live evidence
is indexed in `docs/evidence/README.md`; `LIVE_E2E.json` is the machine-readable
acceptance source.

## Final strict gate

After the genuine final PDF exists and the final branch is pushed cleanly, run:

```powershell
./scripts/verify-final-delivery.ps1 -RequireFinalState
```

It must pass with a clean worktree and an exactly synchronized
`origin/stage-7.1-final-handoff`. A failure is a real handoff blocker; fix the
reported artifact, branch, evidence or validation issue rather than bypassing
the gate.
