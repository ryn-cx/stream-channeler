# TODO: Validate
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

$keyring = Join-Path $repoRoot ".venv\Scripts\keyring.exe"
if (-not (Test-Path $keyring)) {
    throw "No keyring executable at $keyring. Run 'uv sync' in the repo root first."
}

$secretNames = @(
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "YOUTUBE_API_KEY",
    "GET_AROUND_SERVER",
    "CF_ACCESS_CLIENT_ID",
    "CF_ACCESS_CLIENT_SECRET",
    "TMDB_API_READ_TOKEN"
)
$missing = @()
foreach ($secretName in $secretNames) {
    $value = & $keyring get get-around $secretName 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($value)) {
        $missing += $secretName
        continue
    }
    Set-Item -Path "env:$secretName" -Value $value.Trim()
}
if ($missing.Count -gt 0) {
    $commands = ($missing | ForEach-Object { "  .venv\Scripts\keyring.exe set get-around $_" }) -join "`n"
    throw "These secrets are not in the credential store yet:`n$commands"
}

$environmentFile = Join-Path $repoRoot ".env"
$databasePort = (Select-String -Path $environmentFile -Pattern '^DB_PORT=(.+)$').Matches.Groups[1].Value.Trim()
if ([string]::IsNullOrWhiteSpace($databasePort)) {
    throw "No DB_PORT in $environmentFile"
}
$env:POSTGRES_SERVER = "localhost"
$env:POSTGRES_PORT = $databasePort

Push-Location (Join-Path $repoRoot "backend")
try {
    uv run python -m app.tools.sync_test_files
}
finally {
    Pop-Location
}
