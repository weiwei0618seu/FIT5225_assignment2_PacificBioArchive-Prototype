#!/usr/bin/env bash
set -euo pipefail

region="ap-southeast-2"
stack_name="${PBA_STACK_NAME:-pacific-bioarchive-prototype}"
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ "${PBA_CONFIRM_FREE_PLAN:-}" != 'US$0' ]]; then
  echo "Set PBA_CONFIRM_FREE_PLAN='US$0' only after checking Billing and Free Plan." >&2
  exit 1
fi
for command_name in aws node npm jq; do
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
environment_path="$repository_root/frontend/.env.production.local"

printf '%s\n' \
  "VITE_AWS_REGION=$region" \
  "VITE_API_BASE_URL=$api_url" \
  "VITE_COGNITO_USER_POOL_ID=$user_pool_id" \
  "VITE_COGNITO_CLIENT_ID=$user_pool_client_id" \
  "VITE_COGNITO_DOMAIN=$cognito_domain" \
  "VITE_OAUTH_REDIRECT_URI=$frontend_url/auth/callback" \
  "VITE_OAUTH_LOGOUT_URI=$frontend_url/login" \
  > "$environment_path"

cd "$repository_root/frontend"
npx --yes pnpm@11.19.0 install --frozen-lockfile
npx --yes pnpm@11.19.0 run build
aws s3 sync dist "s3://$frontend_bucket" --delete --region "$region" --only-show-errors
aws cloudfront create-invalidation \
  --distribution-id "$distribution_id" \
  --paths '/*' \
  --output json >/dev/null
printf 'Frontend deployed to %s\n' "$frontend_url"
