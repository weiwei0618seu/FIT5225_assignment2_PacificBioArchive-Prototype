#!/usr/bin/env bash
set -euo pipefail

region="ap-southeast-2"
stack_name="${PBA_STACK_NAME:-pacific-bioarchive-prototype}"
export AWS_PAGER=""

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

for command_name in aws jq curl; do
  command -v "$command_name" >/dev/null 2>&1 || fail "Required command is unavailable: $command_name"
done

# Keep every AWS operation read-only and suppress raw service responses. This
# prevents identifiers, pre-signed URLs, tokens or other response fields from
# being copied into CI logs or assessment evidence by accident.
aws_json() {
  local response
  if ! response="$(aws --no-cli-pager "$@" --region "$region" --output json 2>/dev/null)"; then
    fail "An AWS read failed; check the signed-in role, region and stack state"
  fi
  printf '%s' "$response"
}

stack="$(aws_json cloudformation describe-stacks --stack-name "$stack_name")"
if ! jq -e '.Stacks | length == 1 and .[0].StackStatus == "CREATE_COMPLETE"' \
  <<<"$stack" >/dev/null; then
  fail "The requested stack is not in CREATE_COMPLETE"
fi
pass "CloudFormation stack is CREATE_COMPLETE"

stack_output() {
  local output_key="$1"
  local value
  if ! value="$(jq -er --arg key "$output_key" \
    '.Stacks[0].Outputs[] | select(.OutputKey == $key) | .OutputValue' \
    <<<"$stack" 2>/dev/null)"; then
    fail "Required CloudFormation output is missing"
  fi
  printf '%s' "$value"
}

stack_parameter() {
  local parameter_key="$1"
  local value
  if ! value="$(jq -er --arg key "$parameter_key" \
    '.Stacks[0].Parameters[] | select(.ParameterKey == $key) | .ParameterValue' \
    <<<"$stack" 2>/dev/null)"; then
    fail "Required CloudFormation parameter is missing"
  fi
  printf '%s' "$value"
}

resources="$(aws_json cloudformation list-stack-resources --stack-name "$stack_name")"

physical_id() {
  local logical_id="$1"
  local value
  if ! value="$(jq -er --arg logical "$logical_id" \
    '.StackResourceSummaries[] | select(.LogicalResourceId == $logical) | .PhysicalResourceId' \
    <<<"$resources" 2>/dev/null)"; then
    fail "A required stack resource is missing"
  fi
  printf '%s' "$value"
}

# Include resources owned by nested stacks when proving that the deployment
# does not contain the paid/high-risk services excluded by the project design.
all_resources="$resources"
while IFS= read -r nested_stack; do
  [[ -n "$nested_stack" ]] || continue
  nested_resources="$(aws_json cloudformation list-stack-resources --stack-name "$nested_stack")"
  all_resources="$(jq -sc '{StackResourceSummaries: (.[0].StackResourceSummaries + .[1].StackResourceSummaries)}' \
    <(printf '%s' "$all_resources") <(printf '%s' "$nested_resources"))"
done < <(jq -r '.StackResourceSummaries[] | select(.ResourceType == "AWS::CloudFormation::Stack") | .PhysicalResourceId' \
  <<<"$resources")

if jq -e '[.StackResourceSummaries[].ResourceType | select(test("^AWS::(EC2::|RDS::|OpenSearchService::|SageMaker::|EFS::|WAF)") )] | length > 0' \
  <<<"$all_resources" >/dev/null; then
  fail "The stack contains a service excluded by the free-plan architecture"
fi
pass "No EC2, NAT, RDS, OpenSearch, SageMaker, EFS or WAF resources are in the stack"

ml_image_uri="$(stack_parameter MlImageUri)"
if [[ ! "$ml_image_uri" =~ ^[0-9]{12}\.dkr\.ecr\.ap-southeast-2\.amazonaws\.com/[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$ ]]; then
  fail "The deployed ML image parameter is not an immutable Sydney ECR digest"
fi

for function_spec in \
  'CoreApiFunction:512:Zip' \
  'MediaProcessorFunction:3008:Image' \
  'TemporaryQueryFunction:3008:Image'; do
  IFS=: read -r logical_id expected_memory expected_package <<<"$function_spec"
  function_name="$(physical_id "$logical_id")"
  function_data="$(aws_json lambda get-function --function-name "$function_name")"
  if ! jq -e --argjson memory "$expected_memory" --arg package "$expected_package" \
    '.Configuration.State == "Active" and
     .Configuration.LastUpdateStatus == "Successful" and
     .Configuration.MemorySize == $memory and
     .Configuration.PackageType == $package' \
    <<<"$function_data" >/dev/null; then
    fail "A Lambda function is not active or does not match its bounded configuration"
  fi

  concurrency="$(aws_json lambda get-function-concurrency --function-name "$function_name")"
  if ! jq -e '.ReservedConcurrentExecutions == null' <<<"$concurrency" >/dev/null; then
    fail "A Lambda function has reserved concurrency in the Academy account"
  fi

  if [[ "$expected_package" == 'Image' ]]; then
    if ! jq -e --arg image "$ml_image_uri" '.Code.ResolvedImageUri == $image' \
      <<<"$function_data" >/dev/null; then
      fail "An ML Lambda is not running the immutable digest recorded by the stack"
    fi
  fi
done
pass "All Lambdas are active, bounded, unreserved and use the expected ML digest"

for bucket_logical_id in MediaBucket ModelBucket FrontendBucket; do
  bucket_name="$(physical_id "$bucket_logical_id")"
  public_access="$(aws_json s3api get-public-access-block --bucket "$bucket_name")"
  if ! jq -e '.PublicAccessBlockConfiguration |
    [.BlockPublicAcls, .BlockPublicPolicy, .IgnorePublicAcls, .RestrictPublicBuckets] |
    all(. == true)' <<<"$public_access" >/dev/null; then
    fail "An S3 bucket does not block all public access"
  fi

  encryption="$(aws_json s3api get-bucket-encryption --bucket "$bucket_name")"
  if ! jq -e '.ServerSideEncryptionConfiguration.Rules |
    any(.ApplyServerSideEncryptionByDefault.SSEAlgorithm == "AES256" or
        .ApplyServerSideEncryptionByDefault.SSEAlgorithm == "aws:kms")' \
    <<<"$encryption" >/dev/null; then
    fail "An S3 bucket does not have default encryption"
  fi

  bucket_policy="$(aws_json s3api get-bucket-policy --bucket "$bucket_name")"
  if ! jq -e '.Policy | fromjson | .Statement |
    any(.Effect == "Deny" and
        .Condition.Bool["aws:SecureTransport"] == "false" and
        ((.Action | type == "string") and .Action == "s3:*" or
         (.Action | type == "array") and (.Action | index("s3:*")) != null))' \
    <<<"$bucket_policy" >/dev/null; then
    fail "An S3 bucket policy does not deny insecure transport"
  fi
done
pass "All S3 buckets block public access, encrypt at rest and require TLS"

for table_logical_id in MediaTable DedupTable SubscriptionsTable NotificationEventsTable; do
  table_name="$(physical_id "$table_logical_id")"
  table_data="$(aws_json dynamodb describe-table --table-name "$table_name")"
  if ! jq -e '.Table.TableStatus == "ACTIVE" and
    .Table.BillingModeSummary.BillingMode == "PAY_PER_REQUEST" and
    .Table.SSEDescription.Status == "ENABLED"' <<<"$table_data" >/dev/null; then
    fail "A DynamoDB table is not active, encrypted and on-demand"
  fi
done
pass "All DynamoDB tables are active, encrypted and PAY_PER_REQUEST"

api_id="$(physical_id HttpApi)"
routes="$(aws_json apigatewayv2 get-routes --api-id "$api_id")"
expected_routes='[
  "GET /health",
  "POST /uploads/init",
  "GET /media/{file_id}",
  "POST /queries/tags",
  "GET /queries/species",
  "POST /queries/thumbnail",
  "POST /queries/file/init",
  "POST /queries/file/{query_id}",
  "POST /media/tags",
  "POST /media/delete",
  "POST /notifications/subscription",
  "GET /notifications/subscription",
  "DELETE /notifications/subscription"
]'
if ! jq -e --argjson expected "$expected_routes" '
  [.Items[] | select(.RouteKey != "$default")] as $actual |
  ($actual | length) == ($expected | length) and
  ($actual | all(.AuthorizationType == "JWT" and (.AuthorizerId | length > 0))) and
  (($actual | map(.RouteKey) | sort) == ($expected | sort))' \
  <<<"$routes" >/dev/null; then
  fail "The live API route set is incomplete or a business route is not JWT protected"
fi
pass "Every required live API route uses JWT authorization"

api_url="$(stack_output ApiUrl)"
if [[ ! "$api_url" =~ ^https://[a-z0-9]+\.execute-api\.ap-southeast-2\.amazonaws\.com/?$ ]]; then
  fail "The API output is not a Sydney API Gateway HTTPS endpoint"
fi
if ! health_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
  --max-time 20 "${api_url%/}/health" 2>/dev/null)"; then
  fail "The unauthenticated health request could not be completed"
fi
if [[ "$health_status" != '401' ]]; then
  fail "The unauthenticated health request was not rejected with HTTP 401"
fi
pass "Unauthenticated /health is rejected with HTTP 401"

distribution_id="$(stack_output FrontendDistributionId)"
distribution="$(aws_json cloudfront get-distribution --id "$distribution_id")"
if ! jq -e '.Distribution.Status == "Deployed" and
  .Distribution.DistributionConfig.Enabled == true' <<<"$distribution" >/dev/null; then
  fail "The CloudFront distribution is not enabled and deployed"
fi
pass "CloudFront is enabled and deployed"

for log_group_logical_id in CoreApiLogGroup MediaProcessorLogGroup TemporaryQueryLogGroup; do
  log_group_name="$(physical_id "$log_group_logical_id")"
  log_groups="$(aws_json logs describe-log-groups --log-group-name-prefix "$log_group_name")"
  if ! jq -e --arg exact "$log_group_name" '
    [.logGroups[] | select(.logGroupName == $exact and .retentionInDays == 7)] | length == 1' \
    <<<"$log_groups" >/dev/null; then
    fail "A Lambda log group does not have the required seven-day retention"
  fi
done
pass "All Lambda log groups retain data for seven days"

pass "Live stack verification completed without emitting endpoints, credentials or secrets"
