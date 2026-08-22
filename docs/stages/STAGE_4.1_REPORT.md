# Stage 4.1 Report — Authenticated REST API

## Goal and boundary

Expose the already tested application services through the assignment REST
contract using API Gateway HTTP API v2 events, while keeping ML dependencies out
of the lightweight core Lambda. Cognito resource/JWT-authorizer and IAM template
configuration are Stage 4.2.

## Completed behavior

- Parses HTTP API v2 method, path, query, JSON/base64 body and request ID.
- Requires a Cognito JWT `sub` for every business/health route and propagates
  only trusted `sub`, email and email-verification claims.
- Returns consistent JSON errors with status, stable code, generic safe message,
  request ID and no implementation/credential details.
- Implements upload initiation, owner-aware media status/detail, strict count
  AND queries, species query and thumbnail-to-original lookup.
- Implements temporary-image ticket creation plus a separate ML Lambda handler
  that verifies scope/metadata/checksum, detects tags, performs AND search and
  deletes the temporary object in `finally`.
- Implements assignment-compatible bulk tag editing, idempotent bulk deletion,
  and verified-email notification POST/GET/DELETE.
- Serializes private media as short-lived presigned URLs; durable S3 keys are
  not presented as public resources.
- Preserves bounded detections/confidence evidence and now records/returns the
  configured inference `model_version` per media record.
- Builds real boto3/DynamoDB/S3/SNS service graphs lazily for the core API and
  ML temporary-query functions.

## Created files

- `backend/src/pacific_bioarchive/application/temp_queries.py`
- `backend/src/pacific_bioarchive/handlers/http.py`
- `backend/src/pacific_bioarchive/handlers/api.py`
- `backend/src/pacific_bioarchive/handlers/temp_query.py`
- `backend/tests/unit/test_rest_api.py`
- `docs/stages/STAGE_4.1_REPORT.md`
- `docs/stages/STAGE_4.1_HANDOFF.md`

## Modified files

- `backend/src/pacific_bioarchive/domain/media.py`
- `backend/src/pacific_bioarchive/persistence/dynamodb.py`
- `backend/src/pacific_bioarchive/application/processing.py`
- `backend/tests/unit/test_async_processing.py`
- `docs/API_SPEC.md`
- `docs/DATA_MODEL.md`
- `docs/GENAI_USAGE.md`

## Verification

Command from `backend`:

```powershell
uv run --project . --extra dev pytest -q
```

Observed result: `89 passed` (75 prior regression tests plus 14 REST/temporary
query contract tests). Focused Ruff checks pass for every new Stage 4.1 source
and test file. Python compilation and secret-pattern scans are also performed
before commit.

Contract coverage includes unauthenticated rejection, health, malformed JSON,
upload plus duplicate conflict, signed media detail and pending-record privacy,
all persistent query modes, empty and unknown routes, internal-error redaction,
temporary init/execute/checksum cleanup/cross-handler auth/cross-user isolation,
delete idempotency, and notification claim handling.

## How to run

The core entry point is `pacific_bioarchive.handlers.api.lambda_handler`. The ML
temporary-query entry point is
`pacific_bioarchive.handlers.temp_query.lambda_handler`. Unit tests call their
framework-neutral applications with injected in-memory/fake AWS adapters.

## AWS operations

None. API Gateway, authorizer and functions have not yet been deployed, so no
live URL or JWT success is claimed.

## Known issues and later work

- Stage 4.2 must ensure API Gateway validates issuer/audience/expiry before these
  handlers and applies least-privilege roles to the two functions.
- The supplied-model Linux container still needs real smoke evidence before the
  temporary ML route can be claimed live.
- API pagination currently enforces a bounded result limit and reports
  `truncated`; assignment-scale DynamoDB scans are retained, while a production
  continuation token is intentionally out of scope.
