#!/usr/bin/env bash
set -euo pipefail

region="ap-southeast-2"
stack_name="${PBA_STACK_NAME:-pacific-bioarchive-prototype}"
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
deploy_mode="${PBA_DEPLOY_MODE:-interactive}"
prebuilt_archive="${PBA_PREBUILT_SAM_ARCHIVE:-}"
prebuilt_sha256="${PBA_PREBUILT_SAM_SHA256:-}"
prebuilt_root=""

cleanup() {
  if [[ -n "$prebuilt_root" && "$prebuilt_root" == /tmp/pba-sam-build.* ]]; then
    rm -rf -- "$prebuilt_root"
  fi
}
trap cleanup EXIT

if [[ "${PBA_CONFIRM_FREE_PLAN:-}" != 'US$0' ]]; then
  echo "Set PBA_CONFIRM_FREE_PLAN='US$0' only after checking Billing and Free Plan." >&2
  exit 1
fi
: "${PBA_HOSTED_UI_DOMAIN_PREFIX:?Set a globally unique Cognito domain prefix}"
: "${PBA_ML_IMAGE_URI:?Set the immutable ECR image URI from publish evidence}"
for command_name in aws sam docker; do
  command -v "$command_name" >/dev/null
done
[[ "$deploy_mode" == interactive || "$deploy_mode" == prepare ]]

account_id="$(aws sts get-caller-identity --query Account --output text)"
image_pattern="^${account_id}\\.dkr\\.ecr\\.${region}\\.amazonaws\\.com/[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$"
[[ "$PBA_ML_IMAGE_URI" =~ $image_pattern ]]
[[ "$PBA_HOSTED_UI_DOMAIN_PREFIX" =~ ^[a-z0-9-]{8,63}$ ]]
image_repository="${PBA_ML_IMAGE_URI%@*}"

cd "$repository_root"
sam validate --lint --template-file infrastructure/template.yaml --region "$region"
if [[ -n "$prebuilt_archive" ]]; then
  command -v tar >/dev/null
  command -v sha256sum >/dev/null
  [[ -f "$prebuilt_archive" ]]
  [[ "$prebuilt_sha256" =~ ^[0-9a-f]{64}$ ]]
  actual_sha256="$(sha256sum "$prebuilt_archive" | awk '{print $1}')"
  [[ "$actual_sha256" == "$prebuilt_sha256" ]]

  while IFS= read -r member; do
    [[ "$member" == build || "$member" == build/* ]]
    [[ "$member" != /* && "$member" != ../* && "$member" != *'/../'* ]]
  done < <(tar -tzf "$prebuilt_archive")

  prebuilt_root="$(mktemp -d /tmp/pba-sam-build.XXXXXX)"
  tar --no-same-owner --no-same-permissions -xzf "$prebuilt_archive" \
    -C "$prebuilt_root"
  deploy_template="$prebuilt_root/build/template.yaml"
  [[ -f "$deploy_template" ]]
  echo "Using SHA-256 verified SAM build artifact from the official CI container."
else
  # CloudShell currently provides Python 3.13 while the Lambda ZIP functions
  # use Python 3.12. The official SAM build container supplies the matching
  # runtime and keeps dependency resolution reproducible across deployment
  # hosts.
  sam build --use-container --template-file infrastructure/template.yaml --parallel
  deploy_template="$repository_root/.aws-sam/build/template.yaml"
  [[ -f "$deploy_template" ]]
fi

change_set_option=(--confirm-changeset)
if [[ "$deploy_mode" == prepare ]]; then
  change_set_option=(--no-execute-changeset)
fi

sam deploy \
  --template-file "$deploy_template" \
  --stack-name "$stack_name" \
  --region "$region" \
  --resolve-s3 \
  --image-repository "$image_repository" \
  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
  --parameter-overrides \
    "HostedUiDomainPrefix=$PBA_HOSTED_UI_DOMAIN_PREFIX" \
    "MlImageUri=$PBA_ML_IMAGE_URI" \
    'EnableGoogleFederation=false' \
    'CreateCostBudget=false' \
  "${change_set_option[@]}" \
  --no-fail-on-empty-changeset
