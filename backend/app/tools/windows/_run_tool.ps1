# TODO: Validate
# Shared runner for the scripts beside it.
# Usage: ./_run_tool.ps1 <module> [-IntervalSeconds <n>] [tool args...]
#
# Anything that is not one of this script's own options is passed on to the
# tool, which is how a tool that takes an argument is given one.

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$Module,
    [int]$IntervalSeconds = 0,
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$ToolArguments = @()
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)))

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
# Pushed rather than set, so a caller running this in their own session is left in
# the directory they started in, whether the tool succeeds or throws.
Push-Location (Join-Path $repoRoot "backend")
try {
    while ($true) {
        uv run python -m $Module @ToolArguments
        if ($IntervalSeconds -le 0) {
            break
        }
        Write-Host "Next run in $IntervalSeconds seconds. Ctrl-C to stop."
        Start-Sleep -Seconds $IntervalSeconds
    }
}
finally {
    Pop-Location
}
