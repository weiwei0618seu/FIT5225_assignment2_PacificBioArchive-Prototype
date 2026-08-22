[CmdletBinding()]
param(
    [switch]$RequireFinalState,
    [switch]$SkipValidation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script:passCount = 0

function Assert-Condition {
    param(
        [bool]$Condition,
        [string]$Message
    )
    if (-not $Condition) {
        throw "FINAL DELIVERY GATE FAILED: $Message"
    }
}

function Write-Pass {
    param([string]$Message)
    $script:passCount += 1
    Write-Output "PASS: $Message"
}

function Invoke-Git {
    param([string[]]$GitArguments)
    $output = @(& git @GitArguments 2>&1)
    if ($LASTEXITCODE -ne 0) {
        throw "Git read failed: git $($GitArguments[0])"
    }
    return $output
}

Push-Location $repositoryRoot
try {
    foreach ($commandName in @('git', 'uv', 'uvx', 'pnpm')) {
        Assert-Condition ([bool](Get-Command $commandName -ErrorAction SilentlyContinue)) `
            "Required command is unavailable: $commandName"
    }

    $origin = ((Invoke-Git -GitArguments @('remote', 'get-url', 'origin')) |
        Select-Object -First 1).Trim()
    Assert-Condition ($origin -match '^https://github\.com/weiwei0618seu/FIT5225_assignment2_PacificBioArchive-Prototype(?:\.git)?$') `
        'origin is not the approved Prototype repository'
    Write-Pass 'Only the approved Prototype origin is configured'

    $currentBranch = ((Invoke-Git -GitArguments @('branch', '--show-current')) |
        Select-Object -First 1).Trim()
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($currentBranch)) `
        'the repository is in detached HEAD state'

    $requiredStageBranches = [ordered]@{
        'stage-0-baseline' = '0'
        'stage-1.1-inference-service' = '1.1'
        'stage-1.2-image-processing' = '1.2'
        'stage-1.3-video-processing' = '1.3'
        'stage-2.1-domain-persistence' = '2.1'
        'stage-2.2-query-engine' = '2.2'
        'stage-2.3-media-management' = '2.3'
        'stage-3.1-s3-upload-workflow' = '3.1'
        'stage-3.2-async-processing' = '3.2'
        'stage-3.3-notifications' = '3.3'
        'stage-4.1-rest-api' = '4.1'
        'stage-4.2-cognito-iam' = '4.2'
        'stage-5.1-ui-auth' = '5.1'
        'stage-5.2-ui-upload-results' = '5.2'
        'stage-5.3-ui-queries' = '5.3'
        'stage-5.4-ui-management' = '5.4'
        'stage-6.1-infrastructure' = '6.1'
        'stage-6.2-integration-e2e' = '6.2'
        'stage-6.3-aws-deployment' = '6.3'
    }
    $remoteBranches = @(Invoke-Git -GitArguments @(
        'for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin/stage-*'
    ))
    foreach ($entry in $requiredStageBranches.GetEnumerator()) {
        $remoteBranch = "origin/$($entry.Key)"
        Assert-Condition ($remoteBranches -contains $remoteBranch) `
            "missing pushed stage branch: $($entry.Key)"
        & git merge-base --is-ancestor $remoteBranch HEAD 2>$null
        Assert-Condition ($LASTEXITCODE -eq 0) `
            "stage branch is not an ancestor of the current delivery: $($entry.Key)"
        foreach ($kind in @('REPORT', 'HANDOFF')) {
            $stageDocument = "docs/stages/STAGE_$($entry.Value)_$kind.md"
            Assert-Condition (Test-Path -LiteralPath $stageDocument -PathType Leaf) `
                "missing stage document: $stageDocument"
        }
    }
    Write-Pass 'All 19 sequential stage branches and 38 stage documents exist'

    $requiredDocuments = @(
        'README.md',
        '.env.example',
        'docs/MASTER_PLAN.md',
        'docs/ARCHITECTURE.md',
        'docs/ARCHITECTURE_DECISIONS.md',
        'docs/API_SPEC.md',
        'docs/DATA_MODEL.md',
        'docs/TEST_PLAN.md',
        'docs/DEPLOYMENT_GUIDE.md',
        'docs/USER_GUIDE.md',
        'docs/DEMO_PLAN.md',
        'docs/GENAI_USAGE.md',
        'docs/HD_RUBRIC_AUDIT.md',
        'docs/TEAM_HANDOFF_PLAN.md',
        'docs/OFFICIAL_REPO_INTEGRATION_PLAN.md',
        'docs/report/Pacific_BioArchive_Team_Report_DRAFT.docx'
    )
    foreach ($relativePath in $requiredDocuments) {
        Assert-Condition (Test-Path -LiteralPath $relativePath -PathType Leaf) `
            "missing required delivery document: $relativePath"
    }
    Write-Pass 'All required planning, design, operation and handoff documents exist'

    $requiredImplementation = @(
        'backend/src/pacific_bioarchive/ml/inference.py',
        'backend/src/pacific_bioarchive/application/uploads.py',
        'backend/src/pacific_bioarchive/application/processing.py',
        'backend/src/pacific_bioarchive/application/queries.py',
        'backend/src/pacific_bioarchive/application/temp_queries.py',
        'backend/src/pacific_bioarchive/application/management.py',
        'backend/src/pacific_bioarchive/application/notifications.py',
        'backend/src/pacific_bioarchive/handlers/api.py',
        'backend/src/pacific_bioarchive/handlers/media_processor.py',
        'backend/src/pacific_bioarchive/handlers/temp_query.py',
        'frontend/src/App.tsx',
        'frontend/src/pages/UploadPage.tsx',
        'frontend/src/pages/SearchPage.tsx',
        'frontend/src/pages/ManagePage.tsx',
        'infrastructure/template.yaml',
        'infrastructure/auth-and-iam.json',
        'infrastructure/scripts/verify-live-stack.sh'
    )
    foreach ($relativePath in $requiredImplementation) {
        Assert-Condition (Test-Path -LiteralPath $relativePath -PathType Leaf) `
            "missing required implementation surface: $relativePath"
    }
    Write-Pass 'Every core assignment capability has an implementation surface'

    $trackedFiles = @(Invoke-Git -GitArguments @('ls-files'))
    $forbiddenTracked = @($trackedFiles | Where-Object {
        (($_ -match '(^|/)\.env($|\.)') -and $_ -ne '.env.example') -or
        $_ -match '\.(pem|key)$' -or
        $_ -match '(^|/)samconfig\.toml$' -or
        $_ -match '(^|/)(node_modules|dist|coverage|__pycache__)/'
    })
    Assert-Condition ($forbiddenTracked.Count -eq 0) `
        'a secret/local/build artifact path is tracked'

    $textExtensions = @(
        '.css', '.html', '.js', '.json', '.jsx', '.md', '.ps1', '.py', '.sh',
        '.toml', '.ts', '.tsx', '.txt', '.yaml', '.yml'
    )
    $secretPattern = '(?im)(?:AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|aws_secret_access_key\s*[:=]\s*["'']?[A-Za-z0-9/+=]{20,})'
    # Split the POSIX marker so this scanner does not match its own source.
    $absolutePathPattern = '(?i)(?:[A-Z]:\\(?:Users|Desktop)\\|' +
        '/' + 'Users/[^/\s]+/)'
    foreach ($relativePath in $trackedFiles) {
        $extension = [IO.Path]::GetExtension($relativePath)
        $leaf = [IO.Path]::GetFileName($relativePath)
        $isText = $textExtensions -contains $extension -or
            $leaf -in @('Dockerfile', 'Dockerfile.ml', '.env.example')
        if (-not $isText) {
            continue
        }
        $content = [IO.File]::ReadAllText((Join-Path $repositoryRoot $relativePath))
        Assert-Condition (-not [regex]::IsMatch($content, $secretPattern)) `
            "possible committed credential in $relativePath"
        if ($extension -ne '.md' -and $extension -ne '.txt') {
            Assert-Condition (-not [regex]::IsMatch($content, $absolutePathPattern)) `
                "non-portable local absolute path in $relativePath"
        }
    }
    Write-Pass 'Tracked text contains no credential pattern or runtime local absolute path'

    $expectedLfsFiles = @(
        'legacy/PacificBioArchive/mdv5a.pt',
        'legacy/PacificBioArchive/model.pt'
    )
    $actualLfsFiles = @(Invoke-Git -GitArguments @('lfs', 'ls-files', '--name-only') |
        ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $lfsDifference = @(Compare-Object -ReferenceObject $expectedLfsFiles `
        -DifferenceObject $actualLfsFiles)
    Assert-Condition ($lfsDifference.Count -eq 0) `
        'the supplied model files are not exactly the two expected Git LFS objects'
    foreach ($modelPath in $expectedLfsFiles) {
        Assert-Condition ((Get-Item -LiteralPath $modelPath).Length -gt 1MB) `
            "model content is an unfetched LFS pointer: $modelPath"
    }
    $null = Invoke-Git -GitArguments @('lfs', 'fsck')
    Write-Pass 'Both supplied model weights are present and pass Git LFS integrity checks'

    if ($RequireFinalState) {
        Assert-Condition ($currentBranch -eq 'stage-7.1-final-handoff') `
            'final-state verification must run on stage-7.1-final-handoff'

        $finalArtifacts = @(
            'docs/evidence/LIVE_STACK_ACCEPTANCE.txt',
            'docs/evidence/LIVE_E2E.json',
            'docs/evidence/live-ui/01-login-protected.png',
            'docs/evidence/live-ui/02-upload-ml-thumbnail.png',
            'docs/evidence/live-ui/03-query-management.png',
            'docs/evidence/live-ui/04-notification-logout.png',
            'docs/report/Pacific_BioArchive_Team_Report_FINAL.pdf',
            'docs/stages/STAGE_7.1_REPORT.md',
            'docs/stages/STAGE_7.1_HANDOFF.md'
        )
        foreach ($relativePath in $finalArtifacts) {
            Assert-Condition ($trackedFiles -contains $relativePath) `
                "missing tracked final-state evidence: $relativePath"
        }

        $liveAcceptance = Get-Content -LiteralPath `
            'docs/evidence/LIVE_STACK_ACCEPTANCE.txt' -Raw
        foreach ($expectedPass in @(
            'PASS: CloudFormation stack is CREATE_COMPLETE',
            'PASS: All Lambdas are active, bounded, unreserved and use the expected ML digest',
            'PASS: All S3 buckets block public access, encrypt at rest and require TLS',
            'PASS: All DynamoDB tables are active, encrypted and PAY_PER_REQUEST',
            'PASS: Every required live API route uses JWT authorization',
            'PASS: Unauthenticated /health is rejected with HTTP 401',
            'PASS: CloudFront is enabled and deployed',
            'PASS: All Lambda log groups retain data for seven days'
        )) {
            Assert-Condition ($liveAcceptance.Contains($expectedPass)) `
                "live stack acceptance is missing: $expectedPass"
        }
        Assert-Condition ($liveAcceptance -notmatch '(?im)^FAIL:|https?://|arn:aws:|x-amz-|eyJ') `
            'live stack evidence contains a failure or a sensitive endpoint/identifier'

        $liveE2e = Get-Content -LiteralPath 'docs/evidence/LIVE_E2E.json' -Raw |
            ConvertFrom-Json
        Assert-Condition ($liveE2e.status -eq 'PASS') `
            'live E2E evidence is not PASS'

        $stageReport = Get-Content -LiteralPath 'docs/stages/STAGE_6.3_REPORT.md' -Raw
        Assert-Condition ($stageReport -notmatch '\*\*In progress\.\*\*|\| Pending') `
            'Stage 6.3 report still declares incomplete live gates'

        $remoteFinal = @(Invoke-Git -GitArguments @(
            'for-each-ref', '--format=%(refname:short)',
            'refs/remotes/origin/stage-7.1-final-handoff'
        ))
        Assert-Condition ($remoteFinal -contains 'origin/stage-7.1-final-handoff') `
            'final handoff branch has not been pushed'
        $syncCounts = ((Invoke-Git -GitArguments @(
            'rev-list', '--left-right', '--count',
            'HEAD...origin/stage-7.1-final-handoff'
        )) | Select-Object -First 1) -split '\s+'
        Assert-Condition ($syncCounts[0] -eq '0' -and $syncCounts[1] -eq '0') `
            'final branch differs from its pushed remote'
        Assert-Condition (@(Invoke-Git -GitArguments @('status', '--porcelain')).Count -eq 0) `
            'final worktree is not clean'
        Write-Pass 'Live evidence, final report, final branch and clean synchronization are complete'
    }

    if (-not $SkipValidation) {
        & (Join-Path $repositoryRoot 'infrastructure/scripts/validate.ps1')
        Assert-Condition ($LASTEXITCODE -eq 0) 'the complete local validation gate failed'
        Write-Pass 'Complete backend, frontend, lint, build and template validation passed'
    }

    Write-Output "FINAL DELIVERY GATE PASSED: $script:passCount checks"
}
finally {
    Pop-Location
}
