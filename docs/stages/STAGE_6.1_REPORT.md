# Stage 6.1 Report — Serverless infrastructure and deployment controls

## Goal and boundary

Integrate the tested application into one reviewable SAM/CloudFormation stack
with private storage, authenticated routes, bounded ML compute, observability,
reproducible builds and free-plan safety controls. This stage validates but does
not create AWS resources.

## Completed infrastructure

- Root SAM template deploys a private media bucket, versioned model archive,
  private SPA bucket/CloudFront OAC, four on-demand encrypted DynamoDB tables,
  SNS topic, nested Cognito/IAM application, JWT-authorized HTTP API, lightweight
  ZIP Lambda and two commands from a pinned ML container.
- Declares all 13 authenticated business routes against one Cognito
  issuer/audience authorizer and exact CloudFront/localhost API CORS origins.
- Media PUT/GET CORS permits only required signed headers and origins; every
  bucket blocks public ACLs/policies, enforces bucket ownership and denies
  non-TLS requests.
- EventBridge receives S3 service events, filters the `originals/` prefix,
  transforms to the tested handler event and retries at most twice within one
  hour.
- API concurrency is 2; each heavy Lambda is concurrency 1, maximum 4096 MiB,
  and timeout 15/5 minutes. HTTP API is throttled at 5 requests/second.
- Query-temp objects and incomplete multipart uploads expire/abort after one
  day; Lambda logs retain seven days; two no-action error alarms are included.
- A region rule rejects every deployment except `ap-southeast-2`; automated
  tests exclude EC2, NAT Gateway, RDS, OpenSearch, SageMaker, EFS and WAF.
- An optional US$1 monthly AWS Budget alerts at US$0.10 actual spend; it defaults
  off because student/lab roles may not grant Budgets permissions.
- Native Cognito can bootstrap without OAuth secrets. Enabling Google requires
  both transient NoEcho values and uses exact generated redirect URLs.
- Added explicit-confirmation deployment scripts and a separate frontend build/
  private S3 sync script. The secret-free core script cannot accept Google
  credentials.

## Model build compatibility

The original combined dependency set was objectively unsatisfiable:
MegaDetector pins protobuf `<=3.20.1` while modern ONNX requires a newer line.
The new multi-stage build separates them:

1. build stage: supplied `model.pt` + pinned ONNX/onnx2torch/protobuf 6;
2. trace fixed `[1,480,480,3]` input to TorchScript;
3. compare original/traced `[1,46]` outputs with strict tolerances;
4. final runtime: MegaDetector 10.0.24 + protobuf 3.20.1 + TorchScript only.

Observed locally on Python 3.12:

- classifier conversion completed and returned output shape `(1, 46)`;
- final runtime dependency set resolved and imported Torch 2.7.1,
  torchvision 0.22.1, MegaDetector 10.0.24, OpenCV 4.12.0 and protobuf 3.20.1;
- both `megadetector.detection.run_detector.load_detector` and the TorchScript
  runtime entry points imported successfully.

This is dependency/build evidence, not yet a Linux container build or real
detector+classifier fixture result.

## Verification

```powershell
uv run --project backend --extra dev pytest -q backend/tests
# 103 passed

cd frontend
pnpm run typecheck
pnpm run test:run
pnpm run build
pnpm run lint
# 17 tests; all commands passed

uvx --from cfn-lint cfn-lint infrastructure/template.yaml infrastructure/auth-and-iam.json
# exit 0, no findings

./infrastructure/scripts/validate.ps1
# all available checks passed; warns that SAM CLI is unavailable
```

Seven new infrastructure tests assert the region/cost boundary, absence of
expensive service types, private/encrypted storage, temp lifecycle, on-demand
tables, complete JWT route set, bounded compute/logs and fully pinned model
build.

## Tooling limitation and honest status

AWS CLI, SAM CLI and Docker are not installed on this workstation. Therefore
`sam validate`, `sam build` and the Linux image build are not claimed here.
Stage 6.2 must use an available Linux container builder and record the actual
build and supplied-fixture smoke outputs before any image deployment.

## AWS operations and cost

None. Cloud spend remains unaffected by this stage. No change set, stack, ECR
repository, bucket, distribution, function, table or subscription was created.
