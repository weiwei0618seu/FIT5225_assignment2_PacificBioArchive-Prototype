# Official Repository Integration Plan

Target: private repository
`weiwei0618seu/FIT5225_Assignment2_Group8`. Codex must not modify it during
Prototype development. Four students perform and understand the integration.

## Preparation

1. Protect the official integration branch and keep the repository private.
2. Add all four students and the teaching team with appropriate access.
3. Create a clean baseline containing `.gitignore`, license/course notice and
   an integration checklist; never copy Prototype `.git` history or secrets.
4. Record Prototype final branch/commit and ECR digest in the checklist.

## Student commit order

1. Member 1 adds ML/media code, supplied model acquisition/LFS instructions and
   their tests/evidence.
2. Member 2 adds domain/application/API/query/management code, including the
   temporary-job contract/polling API, and tests.
3. Member 3 adds AWS adapters, EventBridge temporary-query orchestrator/IAM,
   infrastructure, workflows and deployment guide.
4. Member 4 adds Cognito/authentication, frontend and final user/demo documents.

Each member should copy only their owned delta from the final Prototype tree,
resolve interfaces against the already integrated code, run their checks, and
commit from their own account. Do not use one person's account to manufacture
the other members' contribution history.

## Integration rules

- Use the final Prototype dependency files as the single source of versions;
  do not merge four independent lockfiles.
- Preserve module boundaries and avoid duplicate ML/query/auth implementations.
- Resolve configuration through `.env.example` and CloudFormation outputs; no
  Windows absolute paths, tokens, passwords or OAuth secrets.
- Keep model weights in approved Git LFS or documented S3/ECR locations; verify
  pointers are real before the final clone test.
- Keep official branch reviews small enough for another student to explain.

## Final integration gate

Run from a fresh clone:

```powershell
./infrastructure/scripts/validate.ps1
git lfs pull
git status --short
```

Then deploy/rehearse using `docs/DEPLOYMENT_GUIDE.md` and
`docs/DEMO_PLAN.md`. Verify the complete live checklist, scan Git history/files
for secrets, and confirm all four students have substantive commits.

## Report handoff

- Replace member placeholders with confirmed names/IDs and truthful percentages
  (each <=30%).
- Preserve the verified Team Report architecture figure built with official AWS
  icons, and revalidate it if the final integrated architecture changes.
- Include the private official repository link and a concise user guide.
- Explicitly acknowledge Generative AI in Team and Individual Reports; omission
  makes those rubric sections zero.
- Each student writes their own Individual Report/reflection independently.
