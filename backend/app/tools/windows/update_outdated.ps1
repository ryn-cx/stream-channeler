# TODO: Validate
[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.update_outdated" -IntervalSeconds $IntervalSeconds
