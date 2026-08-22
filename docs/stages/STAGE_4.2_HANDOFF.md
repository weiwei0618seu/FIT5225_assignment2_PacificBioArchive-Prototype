# Stage 4.2 Handoff — Cognito, Google Federation and IAM

## What this stage owns

This stage owns the identity contract and permissions boundary: native Cognito
registration/verification, Google federation, SPA OAuth settings, JWT
issuer/audience construction, and the three Lambda execution roles.

## Main files

- `infrastructure/auth-and-iam.json` — deployable nested CloudFormation stack.
- `auth/config.py` — validated JWT authorizer values.
- `docs/AUTHENTICATION.md` — flow, manual Google setup and safety guidance.
- `tests/unit/test_auth_infrastructure.py` — configuration and policy evidence.
- `.env.example` — public/runtime configuration names without values/secrets.

## Verification

Run all 96 backend tests, then run:

```powershell
uvx --from cfn-lint cfn-lint infrastructure/auth-and-iam.json
```

It must exit 0. Also search staged files for access keys, private keys, Google
client values, tokens and passwords before every commit.

## Demo/review questions

- Why does a React SPA use no Cognito client secret?
- What does PKCE protect in the authorization-code flow?
- Why do native and Google users have the same API JWT issuer?
- Where are issuer, audience, signature and expiry validated?
- Why is email from JWT claims rather than request JSON?
- Why do the three Lambda functions have separate roles?
- Which limited wildcard suffixes remain and why are they necessary?

## Live steps requiring a student

Create the Google OAuth client, add the exact Cognito `/oauth2/idpresponse`
redirect, provide credentials as transient `NoEcho` deployment inputs, confirm
one native Cognito email, and run one Google login. Do not paste secrets into a
Codex message, Git file, screenshot, terminal transcript or saved SAM config.
