# HD Rubric Audit

Status legend: **PASS** = observed evidence; **READY** = implementation and
evidence exist but a submission or rehearsal action remains human-owned;
**OPTIONAL** = enhancement beyond the stable core.

| Rubric item | Status | Evidence / remaining responsibility |
|---|---|---|
| 1.1 Cognito sign-up/sign-in/sign-out | PASS | Real sign-up, email verification, sign-in and sign-out pass; a direct post-logout protected-page visit returned to sign-in. |
| 1.2 block/redirect unauthenticated | PASS | CloudFront root redirected to sign-in; all business routes use JWT and `/health` returned 401 anonymously. |
| 1.3 fine-grained IAM | PASS | Live acceptance observed separate bounded Lambdas, private encrypted TLS-only S3, immutable ECR and no excluded services. |
| 2.1.1 upload/checksum dedup | PASS | Real image/video uploads pass and the deployed UI rejected the existing fixture's exact bytes before storage. |
| 2.1.2 thumbnail/video 1 fps | PASS | Live image thumbnail and three samples for a three-second video observed. |
| 2.1.3 ML tagging/DB insertion | PASS | Both live records reached `READY` with supplied-model counts and persisted metadata. |
| 2.2.1 tag/count/species AND | PASS | Live two-condition minimum-count query returned exactly the two qualifying records. |
| 2.2.2 thumbnail to original | PASS | Live signed-thumbnail reverse lookup returned the original action; evidence redacts the URL and identifier. |
| 2.2.3 query by uploaded file | PASS | Live asynchronous success and forced failure both cleaned `query-temp/`; READY/FAILED jobs had one-hour TTL. |
| 2.3.1 bulk tag edit | PASS | Live two-record add/remove passed; repeated absent-remove reported zero changes. |
| 2.3.2 bulk complete delete | PASS | Both records returned `Deleted`, the retry returned `Already absent`, and live S3/media/dedup checks found no residue. |
| 2.3.3 watched-tag email | PASS | Live subscription is `CONFIRMED`; a watched-tag upload reached `READY`, created its event claim and produced the human-observed email. |
| 3.1 auth/upload UI | PASS | Registration/sign-in and authenticated real image/video upload observed; 23 React tests pass. |
| 3.2 queries UI | PASS | Species, strict-AND, thumbnail-reference and temporary-image modes all pass live. |
| 3.3 bulk/usability UI | PASS | Live two-record selection, add/remove, destructive confirmation, outcome list and retry all passed. |
| 3.4 external account | OPTIONAL | Cognito code-flow/PKCE path exists; needs team-owned Google OAuth credentials and live record. |
| 4.1 demo | READY | `DEMO_PLAN.md`, fixtures, member ownership/Q&A; full rehearsal required. |
| 4.2 Team Report | READY | Verified official-icon draft exists; names/IDs, truthful contributions and final PDF export remain human-owned. |
| 4.2 Individual Reports | READY | Each student must independently write/submit their own report. |
| GenAI declaration | PASS/READY | `GENAI_USAGE.md` maintained; must also appear in both submitted report types. |

## Current measured gate

- backend: 121 passed (plus one Windows-only Bash availability skip);
  domain/application coverage 89.39%; Ruff pass;
- frontend: 23 passed; TypeScript, Vitest, build and ESLint pass;
- CloudFormation: cfn-lint pass; infrastructure security assertions pass;
- real supplied model: three expected fixtures pass locally and in Linux;
- immutable ECR publish: workflow run `34317644832`, job `102357119458`,
  immutable digest `sha256:c51c7685bbafcff84baa42e2c5622f7d4503c731b43f2b9a4f7a3ee0ef755e31`,
  successful after the rerun-safe image tag fix;
- deployment toolchain: workflow run `32610702537`, job `97123189935`,
  official SAM Python 3.12 image, container build and pnpm 11.19.0 frontend
  build successful; failed root-stack record deletion waiter returned zero;
- live root stack: asynchronous update `UPDATE_COMPLETE`; ten sanitized
  infrastructure PASS labels; private CloudFront SPA deployed;
- authenticated UI/ML: Cognito registration/sign-in, image/video processing,
  thumbnail, three one-frame-per-second video samples, strict-AND search, bulk
  tag addition and asynchronous temporary query pass live;
- live security/cost: temporary job TTL/SSE/on-demand mode, scoped roles, JWT
  routes and four-log-group sensitive-field scan pass;
- sanitized live E2E: 22 required checks PASS; Cognito and SNS confirmations
  plus watched-tag inbox delivery are human-observed.

Every core live requirement now has observed evidence. Remaining READY items
are submission/rehearsal responsibilities: four truthful member identities and
contributions, the final Team Report PDF, individual reports and team rehearsal.
Google login remains a clearly documented optional enhancement.
