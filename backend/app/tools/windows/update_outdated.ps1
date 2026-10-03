# TODO: Validate
[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60,
    [string[]]$Plugin,
    [switch]$UserChannelsOnly
)

$ErrorActionPreference = "Stop"

$toolArguments = @()
if ($Plugin) {
    $toolArguments += @("--plugin", $Plugin)
}

if ($UserChannelsOnly) {
    $toolArguments += "--user-channels-only"
}

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.update_outdated" -IntervalSeconds $IntervalSeconds -ToolArguments $toolArguments
