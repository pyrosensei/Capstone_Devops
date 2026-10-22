# Generates the local demo secrets that must not be committed.
#
# - Writes METRICS_TOKEN to monitoring/secrets/metrics_token for Prometheus.
# - Mirrors the same value into the local .env file (created from .env.example
#   when it does not exist yet).
#
# Usage: powershell -ExecutionPolicy Bypass -File scripts/setup-secrets.ps1

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$secretDir = Join-Path $repoRoot "monitoring/secrets"
$tokenFile = Join-Path $secretDir "metrics_token"
$envFile = Join-Path $repoRoot ".env"

if (-not (Test-Path -LiteralPath $secretDir)) {
    New-Item -ItemType Directory -Path $secretDir | Out-Null
}

function New-RandomHex([int]$count) {
    $bytes = New-Object byte[] $count
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }
    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

$token = ""
if (Test-Path -LiteralPath $tokenFile) {
    $token = (Get-Content -LiteralPath $tokenFile -Raw).Trim()
}
if (-not $token) {
    $token = New-RandomHex 32
    Set-Content -LiteralPath $tokenFile -Value $token -NoNewline
    Write-Host "Generated monitoring/secrets/metrics_token"
} else {
    Write-Host "Reusing existing monitoring/secrets/metrics_token"
}

if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $repoRoot ".env.example") -Destination $envFile
    Write-Host "Created .env from .env.example"
}

$content = Get-Content -LiteralPath $envFile
$updated = $false
$newContent = foreach ($line in $content) {
    if ($line -match '^METRICS_TOKEN=') {
        $updated = $true
        "METRICS_TOKEN=$token"
    } else {
        $line
    }
}
if (-not $updated) {
    $newContent += "METRICS_TOKEN=$token"
}
Set-Content -LiteralPath $envFile -Value $newContent

Write-Host "METRICS_TOKEN is set in .env and monitoring/secrets/metrics_token"
Write-Host "The Prometheus scrape endpoint /metrics now requires this bearer token."
