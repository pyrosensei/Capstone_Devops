$ErrorActionPreference = "Stop"
$baseUrl = if ($env:DEVPLANE_URL) { $env:DEVPLANE_URL } else { "http://127.0.0.1:8000" }
Write-Host "== DevPlane smoke demo ==" -ForegroundColor Cyan
Write-Host "Base URL: $baseUrl"
$env:PYTHONIOENCODING = "utf-8"
if (Get-Command conda -ErrorAction SilentlyContinue) {
    conda run -n capstone_devops python scripts/smoke.py --base-url $baseUrl
} else {
    python scripts/smoke.py --base-url $baseUrl
}
