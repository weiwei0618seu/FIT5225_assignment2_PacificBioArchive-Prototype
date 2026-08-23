[CmdletBinding()]
param(
    [string]$StackName = 'pacific-bioarchive-prototype',
    [switch]$ConfirmDeploy
)

$ErrorActionPreference = 'Stop'
$region = 'ap-southeast-2'
$repositoryRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
if (-not $ConfirmDeploy) { throw 'Re-run with -ConfirmDeploy after the core stack is CREATE_COMPLETE.' }
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) { throw 'AWS CLI is required.' }

$rawOutputs = aws cloudformation describe-stacks --stack-name $StackName --region $region --query 'Stacks[0].Outputs' --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Unable to read CloudFormation outputs.' }
$outputs = @{}
foreach ($item in $rawOutputs) { $outputs[$item.OutputKey] = $item.OutputValue }
foreach ($required in @('ApiUrl', 'FrontendUrl', 'FrontendBucketName', 'FrontendDistributionId', 'UserPoolId', 'UserPoolClientId', 'CognitoHostedUiUrl')) {
    if (-not $outputs[$required]) { throw "Missing stack output $required." }
}
$googleFederation = aws cloudformation describe-stacks --stack-name $StackName --region $region --query 'Stacks[0].Parameters[?ParameterKey==`EnableGoogleFederation`].ParameterValue | [0]' --output text
if ($LASTEXITCODE -ne 0 -or $googleFederation -notin @('true', 'false')) { throw 'Unable to read the Google federation stack parameter.' }

$environmentPath = Join-Path $repositoryRoot 'frontend\.env.production.local'
$environment = @(
    "VITE_AWS_REGION=$region",
    "VITE_API_BASE_URL=$($outputs.ApiUrl)",
    "VITE_COGNITO_USER_POOL_ID=$($outputs.UserPoolId)",
    "VITE_COGNITO_CLIENT_ID=$($outputs.UserPoolClientId)",
    "VITE_COGNITO_DOMAIN=$($outputs.CognitoHostedUiUrl)",
    "VITE_ENABLE_GOOGLE_FEDERATION=$googleFederation",
    "VITE_OAUTH_REDIRECT_URI=$($outputs.FrontendUrl)/auth/callback",
    "VITE_OAUTH_LOGOUT_URI=$($outputs.FrontendUrl)/login"
)
[System.IO.File]::WriteAllLines($environmentPath, $environment, [System.Text.UTF8Encoding]::new($false))

Push-Location (Join-Path $repositoryRoot 'frontend')
try {
    $pnpmVersion = pnpm --version
    if ($LASTEXITCODE -ne 0 -or $pnpmVersion.Trim() -ne '11.19.0') { throw 'pnpm 11.19.0 is required.' }
    pnpm install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency verification failed.' }
    pnpm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    aws s3 sync dist "s3://$($outputs.FrontendBucketName)" --delete --region $region --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw 'Frontend S3 sync failed.' }
    aws cloudfront create-invalidation --distribution-id $outputs.FrontendDistributionId --paths '/*' --output json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'CloudFront invalidation failed.' }
    Write-Host "Frontend deployed to $($outputs.FrontendUrl)"
}
finally {
    Pop-Location
}
