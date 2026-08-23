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

## ADR-011 — Cognito managed login, PKCE and Google federation

The browser is a public OAuth client, so it has no client secret and uses the
authorization-code flow with PKCE. Native registration and Google both terminate
at Cognito; API Gateway therefore validates one issuer/audience pair. Google
client credentials are mandatory `NoEcho` deployment inputs for the HD build
and never become Lambda or frontend environment variables.

## ADR-012 — Separate least-privilege Lambda roles

The core API, upload processor and temporary-query ML function have different
data paths, so each receives its own role. Inline policies name exact table,
topic and S3-prefix ARNs. There is no star action. The sole global resource is
limited to `GetSubscriptionAttributes`, `SetSubscriptionAttributes` and
`Unsubscribe`, because AWS SNS does not support resource-level IAM for those
three lifecycle APIs. `Subscribe` and `Publish` remain restricted to the one
configured topic, while S3 and DynamoDB permissions remain resource-bound.

## ADR-013 — Private CloudFront SPA origin

The SPA bucket also blocks all public access. CloudFront uses origin access
control and SigV4, redirects viewers to HTTPS and maps 403/404 to `index.html`
for client routing. This supplies the HTTPS callbacks required by Cognito and
Google without a public S3 website endpoint.

## ADR-014 — EventBridge S3 delivery

The media bucket publishes AWS service events to EventBridge. A prefix-filtered
rule transforms `originals/` object-created events to the handler's tested S3
event contract. This avoids a CloudFormation dependency cycle between the
bucket, nested least-privilege role and image Lambda while retaining bounded
retry and event age.

## ADR-015 — Isolated classifier conversion

MegaDetector declares protobuf `<=3.20.1`; modern ONNX needed to unpickle the
provided onnx2torch classifier requires newer protobuf. Mixing them produced an
unsatisfiable environment. A multi-stage image build therefore loads the exact
provided `model.pt` with a separate ONNX/protobuf-6 toolchain, traces its fixed
`[1,480,480,3]` input to TorchScript, verifies matching `[1,46]` values, and
copies only that artifact into the MegaDetector/protobuf-3 runtime. No model is
retrained and the source weights remain authoritative.

## ADR-016 — Secret-free native-auth bootstrap

The root stack defaults Google federation off so core AWS resources can be
deployed and produce the exact CloudFront/Cognito redirect URLs without putting
OAuth secrets in a command line or file. A CloudFormation rule requires both
NoEcho Google values when the flag is later enabled for the HD deployment.
