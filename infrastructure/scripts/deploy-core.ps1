[CmdletBinding()]
param(
    [string]$StackName = 'pacific-bioarchive-prototype',
    [Parameter(Mandatory)] [string]$HostedUiDomainPrefix,
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
Write-Host "Deploying account $($identity.Account), region $region, stack $StackName"
Write-Host 'Google federation is intentionally disabled for this secret-free bootstrap.'

Push-Location $repositoryRoot
try {
    sam build --template-file infrastructure/template.yaml --parallel
    if ($LASTEXITCODE -ne 0) { throw 'SAM build failed.' }
    sam deploy `
        --stack-name $StackName `
        --region $region `
        --resolve-s3 `
        --resolve-image-repos `
        --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND `
        --parameter-overrides "HostedUiDomainPrefix=$HostedUiDomainPrefix" 'EnableGoogleFederation=false' 'CreateCostBudget=false' `
        --no-confirm-changeset `
        --no-fail-on-empty-changeset
    if ($LASTEXITCODE -ne 0) { throw 'SAM deployment failed.' }
}
finally {
    Pop-Location
}
