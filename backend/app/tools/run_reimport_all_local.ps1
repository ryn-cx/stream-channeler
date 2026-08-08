# Re-import every show on the host, against the compose database.
#
# The same run as `run_import_queue_local.ps1` - the repo's own venv, the working
# tree as it is on disk, the database compose publishes - pointed at the reimport
# tool instead of the import queue. Every show the plugin user owns is updated with
# `force=True`, so nothing is skipped for being current and the run takes as long
# as the whole library does.
#
# Run it from anywhere:  powershell -File backend\app\tools\run_reimport_all_local.ps1

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# The script lives in backend/app/tools, so the repo root is three levels up.
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))

$keyring = Join-Path $repoRoot ".venv\Scripts\keyring.exe"
if (-not (Test-Path $keyring)) {
    throw "No keyring executable at $keyring. Run 'uv sync' in the repo root first."
}

# The same store and service name `scripts/load-secrets.sh` reads on the server.
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

# `DB_PORT` is what compose publishes the database on; the `POSTGRES_PORT` in `.env`
# is the port inside the network, which nothing on the host can reach.
$environmentFile = Join-Path $repoRoot ".env"
$databasePort = (Select-String -Path $environmentFile -Pattern '^DB_PORT=(.+)$').Matches.Groups[1].Value.Trim()
if ([string]::IsNullOrWhiteSpace($databasePort)) {
    throw "No DB_PORT in $environmentFile"
}
$env:POSTGRES_SERVER = "localhost"
$env:POSTGRES_PORT = $databasePort

# `.env` is loaded from the working directory, which is also where `app` is importable.
Set-Location (Join-Path $repoRoot "backend")
uv run python -m app.tools.reimport_all
