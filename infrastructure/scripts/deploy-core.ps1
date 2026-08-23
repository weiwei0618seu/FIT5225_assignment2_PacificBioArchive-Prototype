[CmdletBinding()]
param(
    [string]$StackName = 'pacific-bioarchive-prototype',
    [Parameter(Mandatory)] [string]$HostedUiDomainPrefix,
    [Parameter(Mandatory)] [string]$MlImageUri,
    [switch]$ConfirmDeploy
)

$ErrorActionPreference = 'Stop'
$region = 'ap-southeast-2'
$repositoryRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')

if (-not $ConfirmDeploy) {
    throw 'Deployment is disabled by default. Re-run with -ConfirmDeploy only after checking AWS Billing/Free Plan is US$0 and the CloudFormation change set contains no paid services.'
}
foreach ($command in @('aws', 'sam', 'docker')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
        throw "$command is required for this deployment path."
    }
}

$identity = aws sts get-caller-identity --output json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $identity.Account) { throw 'AWS identity check failed.' }
$imagePattern = '^(?<Account>[0-9]{12})\.dkr\.ecr\.ap-southeast-2\.amazonaws\.com/[a-z0-9][a-z0-9._/-]*@sha256:[0-9a-f]{64}$'
if ($MlImageUri -notmatch $imagePattern) {
    throw 'MlImageUri must be an immutable ap-southeast-2 ECR digest URI.'
}
if ($Matches.Account -ne $identity.Account) {
    throw 'MlImageUri must belong to the currently authenticated AWS account.'
}
$imageRepository = $MlImageUri.Split('@')[0]
Write-Host "Deploying account $($identity.Account), region $region, stack $StackName"
Write-Host 'Google federation is intentionally disabled for this secret-free bootstrap.'
Write-Host "ML image: $MlImageUri"

Push-Location $repositoryRoot
try {
    # Use the Lambda Python 3.12 build image instead of depending on the host's
    # Python version. This is also the deployment path used in CloudShell.
    sam build --use-container --template-file infrastructure/template.yaml --parallel
    if ($LASTEXITCODE -ne 0) { throw 'SAM build failed.' }
    sam deploy `
        --stack-name $StackName `
        --region $region `
        --resolve-s3 `
        --image-repository $imageRepository `
        --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND `
        --parameter-overrides "HostedUiDomainPrefix=$HostedUiDomainPrefix" "MlImageUri=$MlImageUri" 'EnableGoogleFederation=false' 'CreateCostBudget=false' `
        --confirm-changeset `
        --no-fail-on-empty-changeset
    if ($LASTEXITCODE -ne 0) { throw 'SAM deployment failed.' }
}
finally {
    Pop-Location
}
