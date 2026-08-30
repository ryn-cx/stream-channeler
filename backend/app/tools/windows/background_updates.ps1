# TODO: Validate
[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.background_updates" -IntervalSeconds $IntervalSeconds
