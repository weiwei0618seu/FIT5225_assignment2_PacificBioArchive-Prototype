[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repositoryRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')

Push-Location $repositoryRoot
try {
    uv run --project backend --extra dev pytest -q backend/tests `
        --cov=pacific_bioarchive.domain `
        --cov=pacific_bioarchive.application `
        --cov-report=term-missing `
        --cov-fail-under=85
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
    uvx ruff check backend
    if ($LASTEXITCODE -ne 0) { throw 'Backend Ruff lint failed.' }

    Push-Location (Join-Path $repositoryRoot 'frontend')
    try {
        pnpm install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency verification failed.' }
        pnpm run typecheck
        if ($LASTEXITCODE -ne 0) { throw 'Frontend typecheck failed.' }
        pnpm run test:run
        if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed.' }
        pnpm run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
        pnpm run lint
        if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed.' }
    }
    finally {
        Pop-Location
    }

    uvx --from cfn-lint cfn-lint infrastructure/template.yaml infrastructure/auth-and-iam.json infrastructure/github-oidc-bootstrap.yaml
    if ($LASTEXITCODE -ne 0) { throw 'CloudFormation lint failed.' }

    if (Get-Command sam -ErrorAction SilentlyContinue) {
        sam validate --lint --template-file infrastructure/template.yaml --region ap-southeast-2
        if ($LASTEXITCODE -ne 0) { throw 'SAM validation failed.' }
    }
    else {
        Write-Warning 'AWS SAM CLI is unavailable; cfn-lint and template unit tests were run.'
    }
}
finally {
    Pop-Location
}
