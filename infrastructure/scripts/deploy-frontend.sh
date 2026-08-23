#!/usr/bin/env bash
set -euo pipefail

region="ap-southeast-2"
stack_name="${PBA_STACK_NAME:-pacific-bioarchive-prototype}"
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
prebuilt_archive="${PBA_PREBUILT_FRONTEND_ARCHIVE:-}"
prebuilt_sha256="${PBA_PREBUILT_FRONTEND_SHA256:-}"
prebuilt_root=""

cleanup() {
  if [[ -n "$prebuilt_root" && "$prebuilt_root" == /tmp/pba-frontend.* ]]; then
    rm -rf -- "$prebuilt_root"
  fi
}
trap cleanup EXIT

if [[ "${PBA_CONFIRM_FREE_PLAN:-}" != 'US$0' ]]; then
  echo "Set PBA_CONFIRM_FREE_PLAN='US$0' only after checking Billing and Free Plan." >&2
  exit 1
fi
for command_name in aws jq; do
  command -v "$command_name" >/dev/null
done

outputs="$(aws cloudformation describe-stacks \
  --stack-name "$stack_name" \
  --region "$region" \
  --query 'Stacks[0].Outputs' \
  --output json)"
stack_output() {
  jq -er --arg key "$1" '.[] | select(.OutputKey == $key) | .OutputValue' <<<"$outputs"
}

api_url="$(stack_output ApiUrl)"
frontend_url="$(stack_output FrontendUrl)"
frontend_bucket="$(stack_output FrontendBucketName)"
distribution_id="$(stack_output FrontendDistributionId)"
user_pool_id="$(stack_output UserPoolId)"
user_pool_client_id="$(stack_output UserPoolClientId)"
cognito_domain="$(stack_output CognitoHostedUiUrl)"
google_federation="$(aws cloudformation describe-stacks \
  --stack-name "$stack_name" \
  --region "$region" \
  --query 'Stacks[0].Parameters[?ParameterKey==`EnableGoogleFederation`].ParameterValue | [0]' \
  --output text)"
[[ "$google_federation" == 'true' || "$google_federation" == 'false' ]]
environment_path="$repository_root/frontend/.env.production.local"

printf '%s\n' \
  "VITE_AWS_REGION=$region" \
  "VITE_API_BASE_URL=$api_url" \
  "VITE_COGNITO_USER_POOL_ID=$user_pool_id" \
  "VITE_COGNITO_CLIENT_ID=$user_pool_client_id" \
  "VITE_COGNITO_DOMAIN=$cognito_domain" \
  "VITE_ENABLE_GOOGLE_FEDERATION=$google_federation" \
  "VITE_OAUTH_REDIRECT_URI=$frontend_url/auth/callback" \
  "VITE_OAUTH_LOGOUT_URI=$frontend_url/login" \
  > "$environment_path"

deploy_root="$repository_root/frontend/dist"
if [[ -n "$prebuilt_archive" ]]; then
  for command_name in sha256sum unzip; do
    command -v "$command_name" >/dev/null
  done
  [[ -f "$prebuilt_archive" ]]
  [[ "$prebuilt_sha256" =~ ^[0-9a-f]{64}$ ]]
  actual_sha256="$(sha256sum "$prebuilt_archive" | awk '{print $1}')"
  [[ "$actual_sha256" == "$prebuilt_sha256" ]]
  unzip -tqq "$prebuilt_archive"
  while IFS= read -r member; do
    [[ -n "$member" ]]
    [[ "$member" != /* && "$member" != ../* && "$member" != *'/../'* ]]
  done < <(unzip -Z1 "$prebuilt_archive")

  prebuilt_root="$(mktemp -d /tmp/pba-frontend.XXXXXX)"
  unzip -q "$prebuilt_archive" -d "$prebuilt_root"
  deploy_root="$prebuilt_root"
  [[ -f "$deploy_root/index.html" ]]
  echo "Using SHA-256 verified prebuilt frontend artifact."
else
  for command_name in node npm; do
    command -v "$command_name" >/dev/null
  done
  node -e 'const [major, minor] = process.versions.node.split(".").map(Number); process.exit(major > 22 || (major === 22 && minor >= 13) ? 0 : 1)'
  cd "$repository_root/frontend"
  npx --yes pnpm@11.19.0 install --frozen-lockfile
  npx --yes pnpm@11.19.0 run build
fi
aws s3 sync "$deploy_root" "s3://$frontend_bucket" --delete --region "$region" --only-show-errors
aws cloudfront create-invalidation \
  --distribution-id "$distribution_id" \
  --paths '/*' \
  --output json >/dev/null
printf 'Frontend deployed to %s\n' "$frontend_url"
