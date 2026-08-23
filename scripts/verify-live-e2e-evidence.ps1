[CmdletBinding()]
param(
    [string]$Path = 'docs/evidence/LIVE_E2E.json'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Assert-Evidence {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw "LIVE E2E EVIDENCE FAILED: $Message"
    }
}

Push-Location $repositoryRoot
try {
    Assert-Evidence (Test-Path -LiteralPath $Path -PathType Leaf) `
        "evidence file is missing: $Path"

    $raw = Get-Content -LiteralPath $Path -Raw
    $sensitivePattern = '(?im)(?:https?://|arn:aws:|x-amz-|AKIA[0-9A-Z]{16}|' +
        'ASIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.|' +
        '[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|-----BEGIN [^-]+PRIVATE KEY-----)'
    Assert-Evidence (-not [regex]::IsMatch($raw, $sensitivePattern)) `
        'evidence contains an endpoint, ARN, token, credential, email or signed-request field'

    try {
        $evidence = $raw | ConvertFrom-Json
    }
    catch {
        throw 'LIVE E2E EVIDENCE FAILED: evidence is not valid JSON'
    }

    Assert-Evidence ($evidence.schema_version -eq 1) `
        'schema_version must be 1'
    Assert-Evidence ($evidence.status -eq 'PASS') `
        'top-level status is not PASS'
    Assert-Evidence ($evidence.deployment_region -eq 'ap-southeast-2') `
        'deployment_region is not ap-southeast-2'
    Assert-Evidence ([string]$evidence.model_image_digest -match '^sha256:[0-9a-f]{64}$') `
        'model_image_digest is not an immutable SHA-256 digest'
    Assert-Evidence ($raw -match `
        '"observed_at_utc"\s*:\s*"20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z"') `
        'observed_at_utc is not a second-precision UTC timestamp'

    $requiredChecks = @(
        'protected_route_redirect',
        'unauthenticated_api_401',
        'cognito_register_verify_signin',
        'image_upload_ready',
        'model_prediction_and_confidence',
        'thumbnail_render',
        'duplicate_checksum_rejected',
        'video_one_fps',
        'species_query',
        'strict_and_query',
        'thumbnail_to_original',
        'temporary_query',
        'temporary_success_cleanup',
        'temporary_failure_cleanup',
        'bulk_tag_add',
        'bulk_tag_remove',
        'absent_tag_remove_idempotent',
        'complete_delete',
        'delete_retry_idempotent',
        'sns_watched_tag_delivery',
        'sign_out_blocks_access',
        'cloudwatch_redaction'
    )
    $checks = @($evidence.checks)
    Assert-Evidence ($checks.Count -ge $requiredChecks.Count) `
        'the check collection is incomplete'
    $checkIds = @($checks | ForEach-Object { [string]$_.id })
    Assert-Evidence (@($checkIds | Sort-Object -Unique).Count -eq $checkIds.Count) `
        'check IDs are not unique'
    foreach ($requiredCheck in $requiredChecks) {
        $matches = @($checks | Where-Object { $_.id -eq $requiredCheck })
        Assert-Evidence ($matches.Count -eq 1) `
            "required check is missing: $requiredCheck"
        $check = $matches[0]
        Assert-Evidence ($check.status -eq 'PASS') `
            "required check is not PASS: $requiredCheck"
        Assert-Evidence ([string]$check.source -in @('UI', 'API', 'AWS', 'EMAIL')) `
            "required check has an invalid source: $requiredCheck"
        $note = [string]$check.note
        Assert-Evidence (-not [string]::IsNullOrWhiteSpace($note) -and $note.Length -le 240) `
            "required check needs a concise sanitized note: $requiredCheck"
    }

    $requiredHumanConfirmations = [ordered]@{
        'cognito_email_verification' = 'CONFIRMED'
        'sns_subscription_confirmation' = 'CONFIRMED'
        'sns_watched_tag_delivery' = 'OBSERVED'
    }
    $humanConfirmations = @($evidence.human_confirmations)
    foreach ($entry in $requiredHumanConfirmations.GetEnumerator()) {
        $matches = @($humanConfirmations | Where-Object { $_.id -eq $entry.Key })
        Assert-Evidence ($matches.Count -eq 1 -and $matches[0].status -eq $entry.Value) `
            "human confirmation is missing or incomplete: $($entry.Key)"
    }

    Write-Output `
        "PASS: Sanitized live E2E evidence covers $($requiredChecks.Count) required checks and all human confirmations"
}
finally {
    Pop-Location
}
