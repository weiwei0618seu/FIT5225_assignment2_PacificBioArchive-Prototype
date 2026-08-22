# Test Plan

## Test layers

1. **Unit** — pure checksum, validation, thumbnail, video sampling, label map,
   query predicates, tag mutation, auth context, and serializers.
2. **Adapter** — in-memory repositories and mocked boto3 S3/DynamoDB/SNS.
3. **Contract** — Lambda/API events, status codes, JSON schemas, CORS, JWT
   authorizer template assertions.
4. **Frontend** — components and workflows with mocked HTTP/Cognito clients.
5. **Integration** — local end-to-end orchestration with fake inference and real
   image/video bytes.
6. **ML smoke** — supplied detector/classifier on provided fixtures in the
   pinned container/runtime.
7. **Live AWS E2E** — real registration, verification, upload, S3 event,
   inference, query, tag edit, notification, delete, logout, and rejected access.

## Required coverage matrix

| Requirement | Required evidence |
|---|---|
| single-image ML | structured prediction and confidence |
| species count | two/multiple mocked detections aggregate correctly |
| checksum/dedup | same bytes/different names rejected; concurrent condition tested |
| thumbnail | aspect ratio, dimensions, JPEG compression, EXIF orientation |
| video | samples exactly timestamps 0,1,2… below duration |
| database insertion | complete READY record fields |
| species query | automatic or manual presence returns correct media |
| min count + AND | all conditions required, boundary equality included |
| thumbnail lookup | signed/unsigned URL maps to original |
| temporary query | tags detected; object deleted on success and failure |
| bulk tags | multiple URLs; add/remove; missing delete ignored |
| delete | originals/thumbnails/records/dedup removed; retry safe |
| authorization | unauthenticated blocked; valid subject propagated |
| notification | watched tag only; duplicate event suppressed |
| frontend | loading/success/error/empty/unauthorized states |
| malformed input | safe 4xx without stack trace |
| missing resources | 404 or idempotent success as specified |
| E2E | complete rubric demo order |

## Quality gates

- backend tests: all pass;
- frontend tests: all pass;
- Python coverage target: at least 85% for domain/application code;
- TypeScript lint/typecheck/build: pass;
- no committed secret patterns;
- SAM template validates and least-privilege assertions pass;
- live AWS outcomes clearly separated from mocked/local evidence.

## Recorded Stage 6.2 evidence

- `docs/evidence/LOCAL_MODEL_SMOKE.json` records artifact/fixture SHA-256 values,
  environment, timings and structured detections for three supplied fixtures.
- `test_end_to_end_workflow.py` executes authenticated subscription → upload
  reservation → exact signed headers → verified processing → thumbnail →
  automatic query → manual tag/query → complete deletion in one test.
- `frontend/src/api/client.test.ts` proves a fresh bearer token/no-store request,
  stable error mapping and no network call after local session expiry.
- `.github/workflows/validate-and-smoke.yml` is a manual, no-AWS-credential CI
  path for the full quality gate plus a real x86_64 Linux Lambda-image build and
  supplied two-model smoke. Its result must be linked after an observed run;
  merely committing the workflow is not evidence that the container passed.
- Stage 6.2 measured 90.12% coverage across domain/application code; both local
  validation and CI fail below the declared 85% threshold.
