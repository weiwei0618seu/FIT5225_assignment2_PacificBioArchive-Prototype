#!/usr/bin/env bash
set -euo pipefail

region="ap-southeast-2"
stack_name="${PBA_STACK_NAME:-pacific-bioarchive-prototype}"
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "${PBA_CONFIRM_FREE_PLAN:-}" != 'US$0' ]]; then
  echo "Set PBA_CONFIRM_FREE_PLAN='US$0' only after checking Billing and Free Plan." >&2
  exit 1
fi
: "${PBA_HOSTED_UI_DOMAIN_PREFIX:?Set a globally unique Cognito domain prefix}"
: "${PBA_ML_IMAGE_URI:?Set the immutable ECR image URI from publish evidence}"
for command_name in aws sam; do
  command -v "$command_name" >/dev/null
done

account_id="$(aws sts get-caller-identity --query Account --output text)"
image_pattern="^${account_id}\\.dkr\\.ecr\\.${region}\\.amazonaws\\.com/[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$"
[[ "$PBA_ML_IMAGE_URI" =~ $image_pattern ]]
[[ "$PBA_HOSTED_UI_DOMAIN_PREFIX" =~ ^[a-z0-9-]{8,63}$ ]]

cd "$repository_root"
sam validate --lint --template-file infrastructure/template.yaml --region "$region"
sam build --template-file infrastructure/template.yaml --parallel
sam deploy \
  --stack-name "$stack_name" \
  --region "$region" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --parameter-overrides \
    "HostedUiDomainPrefix=$PBA_HOSTED_UI_DOMAIN_PREFIX" \
    "MlImageUri=$PBA_ML_IMAGE_URI" \
    'EnableGoogleFederation=false' \
    'CreateCostBudget=false' \
  --confirm-changeset \
  --no-fail-on-empty-changeset
