# Stage 4.1 Handoff — Authenticated REST API

## What this stage owns

This stage is the public contract between the React UI and tested application
services. It owns HTTP parsing, trusted claim propagation, route selection,
response serialization and safe error mapping. It also owns the ephemeral query
workflow split between the lightweight API and ML Lambda.

## Main files

- `handlers/http.py` — API Gateway v2 parsing/auth/error boundary.
- `handlers/api.py` — core REST routes and AWS service composition.
- `application/temp_queries.py` — temporary ticket, verification and cleanup.
- `handlers/temp_query.py` — isolated ML route.
- `tests/unit/test_rest_api.py` — end-to-end route contracts with injected AWS
  boundaries.
- `docs/API_SPEC.md` — client-facing request/response reference.

## Verification

Run `uv run --project . --extra dev pytest -q` from `backend` and confirm all 89
tests pass. Then inspect the tests for unauthenticated requests, foreign pending
media, owner-only mutation, generic 500 errors and temporary-object cleanup.

## Demo questions

- Where is the JWT subject obtained, and why is request JSON never trusted for
  user/email identity?
- Why are URLs signed at response time instead of stored in DynamoDB?
- Why does temporary inference run in a separate Lambda container?
- How does the temporary route prevent access to another user's S3 object?
- Which failures still delete the temporary image?
- How does the API avoid leaking AWS/model error details to the browser?

## Live follow-up

After Stage 4.2/6.1, call every route with no token, a valid user token, and an
expired/invalid token. Retain sanitized response/status evidence. A local claim
fixture proves handler behavior but is not evidence that API Gateway's live JWT
authorizer is configured correctly.
