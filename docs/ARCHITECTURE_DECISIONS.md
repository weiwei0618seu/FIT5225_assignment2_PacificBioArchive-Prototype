# Architecture Decisions

## ADR-001 — AWS-only deployment

The project uses AWS only, based on the teaching team's later written
clarification recorded by the students. The original PDF's multi-cloud language
must be acknowledged in the final report and the written clarification retained.

## ADR-002 — AWS SAM infrastructure as code

SAM keeps Lambda/API/S3/DynamoDB/Cognito/SNS definitions in one reviewable
CloudFormation template and supports image-based ML functions. It is easier for
four students to reproduce than manual console-only infrastructure.

## ADR-003 — Separate lightweight API and ML runtimes

Normal APIs do not import PyTorch. Heavy inference runs in dedicated container
functions so CRUD/query endpoints remain fast and inexpensive.

## ADR-004 — Private S3 plus presigned URLs

Public media URLs would conflict with the security requirements. Object keys
are durable; URLs are generated on demand and expire.

## ADR-005 — DynamoDB on-demand tables

The workload is small and bursty. On-demand mode avoids capacity planning and
fits the serverless/free-plan objective.

## ADR-006 — Scan-and-filter query adapter for assignment scale

The domain query engine is correct and testable independently. The initial AWS
adapter scans the small demonstration dataset and evaluates AND/count rules in
code. This avoids a complex inverted-index consistency subsystem. Pagination is
implemented and the limitation is documented; production scale would add a tag
inverted index or OpenSearch, which is intentionally avoided for cost.

## ADR-007 — React + TypeScript + Vite UI

This stack offers clear components, robust typing, fast local tests, and a
static build deployable to S3. The UI remains deliberately simple and demo-safe.

## ADR-008 — Google federation after core stability

Google login is implemented because the Rubric assigns five UI marks, even
though the body calls it bonus. Cognito remains the authorization authority.

## ADR-009 — Canonical species tags

Scientific classifier outputs map to lowercase, human-readable common tags.
Both supplied dingo taxa map to canonical `dingo`; blank common names fall back
to normalized scientific names such as `rattus`.

## ADR-010 — Video count semantics

The assignment specifies 1 fps but not cross-frame identity tracking. Summing
counts would repeatedly count the same stationary animal. The system records
the maximum accepted count per species in any sampled second and records sample
metadata separately.

