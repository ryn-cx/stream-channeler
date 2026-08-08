# Run the import queue on the host, against the compose database.
#
# The simple counterpart of `run_import_queue.ps1`: no image build, no dependency
# dump, no container. The tool runs out of the repo's own venv, so the code it runs
# is the working tree as it is on disk and anything it writes into its dependencies
# stays there. Everything it talks to - the database, the plugins' APIs - is the
# same as the container run.
#
# The database is the one compose publishes, which `.env` gives the container as
# port 5432 (its own port inside the compose network) and the host as `DB_PORT`.
# Only the host port can be reached from here, so it is what gets used.
#
# It keeps running: once a pass finishes it waits `IntervalSeconds` and starts the
# next one. Ctrl-C stops it.
#
# Run it from anywhere:  powershell -File backend\app\tools\run_import_queue_local.ps1

[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60
)

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
while ($true) {
    uv run python -m app.tools.import_queue
    Write-Host "Next run in $IntervalSeconds seconds. Ctrl-C to stop."
    Start-Sleep -Seconds $IntervalSeconds
}
