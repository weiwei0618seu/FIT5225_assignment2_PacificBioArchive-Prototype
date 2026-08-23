# Stage 4.2 Report — Cognito, Google Federation and IAM

## Goal and boundary

Define the authentication resources, JWT-authorizer values and separate
least-privilege Lambda roles needed by the tested API. This stage does not
create AWS resources or supply team-owned Google credentials; the root SAM
stack consumes this subtemplate in Stage 6.1.

## Completed behavior/configuration

- Cognito native registration requires email, given name, family name and a
  strong password; email is automatically verified with a confirmation code.
- Recovery uses verified email only. SMS MFA is disabled to avoid SMS cost and
  unnecessary demo friction.
- SPA client has no secret, prevents user-existence disclosure, uses short
  access/ID tokens, refresh-token revocation, authorization-code flow and
  `openid email profile` scopes.
- Cognito managed login supports both native `COGNITO` and Google federation.
- Google client ID/secret are required `NoEcho` CloudFormation parameters with
  no defaults or repository values.
- Hosted UI callbacks/logout URLs are exact deployment parameters.
- JWT helper produces the Cognito issuer, SPA audience and Authorization-header
  identity source used by the future SAM HTTP API authorizer.
- Core API, media processor and temporary query roles have different table,
  S3-prefix, SNS and model permissions. There is no star action. Live Stage 6.3
  IAM simulation later established that three SNS subscription-lifecycle APIs
  require `Resource: "*"`; that exception is isolated from topic-bound
  `Subscribe`/`Publish` and all data permissions.
- User pool deletion protection plus retain policies reduce accidental identity
  loss.
- Added a complete non-secret `.env.example` for backend/container/SPA public
  identifiers and configuration.

## Created files

- `.env.example`
- `backend/src/pacific_bioarchive/auth/__init__.py`
- `backend/src/pacific_bioarchive/auth/config.py`
- `backend/tests/unit/test_auth_infrastructure.py`
- `infrastructure/auth-and-iam.json`
- `docs/AUTHENTICATION.md`
- `docs/stages/STAGE_4.2_REPORT.md`
- `docs/stages/STAGE_4.2_HANDOFF.md`

## Modified files

- `README.md`
- `docs/ARCHITECTURE_DECISIONS.md`
- `docs/GENAI_USAGE.md`

## Verification

Commands/results:

```powershell
uv run --project . --extra dev pytest -q
# 96 passed

uvx --from cfn-lint cfn-lint infrastructure/auth-and-iam.json
# exit 0, no findings
```

Focused Ruff checks also pass for the new auth source/tests. The seven new tests
verify issuer/audience, invalid identifiers, NoEcho Google inputs, required
registration schema, verification/password/recovery, PKCE-compatible code flow,
Lambda-only trust, absence of global wildcard permissions and role separation.

## AWS operations and manual blockers

None. No Cognito, IAM or Google resources were created. Live HD deployment later
requires a team member to create a Google OAuth Web Application client and
provide its client ID/secret without committing them. Cognito/SNS confirmation
emails also require recipient interaction.

## Known risks/later work

- The root SAM template must wire the JWT issuer/client output into every route
  and attach these role outputs to the correct functions.
- Google redirect/callback/logout URLs must exactly match the final deployed SPA
  and Cognito domain; mismatches produce login loops.
- Live tests must prove invalid/expired/no-token rejection at API Gateway, not
  only the handler's defensive missing-claim test.
