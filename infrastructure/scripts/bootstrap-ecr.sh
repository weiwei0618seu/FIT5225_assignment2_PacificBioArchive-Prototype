#!/usr/bin/env bash
set -euo pipefail

region="ap-southeast-2"
stack_name="${PBA_BOOTSTRAP_STACK_NAME:-pacific-bioarchive-github-bootstrap}"
template_path="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/github-oidc-bootstrap.yaml"

if [[ "${PBA_CONFIRM_FREE_PLAN:-}" != 'US$0' ]]; then
  echo "Set PBA_CONFIRM_FREE_PLAN='US$0' only after checking Billing and Free Plan." >&2
  exit 1
fi
for command_name in aws; do
  command -v "$command_name" >/dev/null
done

account_id="$(aws sts get-caller-identity --query Account --output text)"
[[ "$account_id" =~ ^[0-9]{12}$ ]]
existing_provider="$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[?contains(Arn, 'oidc-provider/token.actions.githubusercontent.com')].Arn | [0]" \
  --output text)"
managed_provider="$(aws cloudformation describe-stack-resource \
  --stack-name "$stack_name" \
  --logical-resource-id GitHubOidcProvider \
  --region "$region" \
  --query 'StackResourceDetail.PhysicalResourceId' \
  --output text 2>/dev/null || true)"

parameters=()
if [[ "$managed_provider" == "$existing_provider" ]]; then
  : # Keep the stack-owned provider managed by this template on repeat deploys.
elif [[ "$existing_provider" != "None" && -n "$existing_provider" ]]; then
  parameters+=("ExistingGitHubOidcProviderArn=$existing_provider")
fi

deploy=(
  aws cloudformation deploy
  --template-file "$template_path"
  --stack-name "$stack_name"
  --region "$region"
  --capabilities CAPABILITY_NAMED_IAM
  --no-fail-on-empty-changeset
)
if ((${#parameters[@]})); then
  deploy+=(--parameter-overrides "${parameters[@]}")
fi
"${deploy[@]}"

aws cloudformation describe-stacks \
  --stack-name "$stack_name" \
  --region "$region" \
  --query "Stacks[0].Outputs[?OutputKey=='EcrRepositoryUri'||OutputKey=='GitHubEcrPushRoleArn'||OutputKey=='TrustedGitHubSubject'].[OutputKey,OutputValue]" \
  --output table
