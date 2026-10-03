# TODO: Validate
[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60,
    [string[]]$Plugin,
    [string[]]$Source,
    [switch]$UserChannelsOnly
)

$ErrorActionPreference = "Stop"

$toolArguments = @()
if ($Plugin) {
    $toolArguments += @("--plugin", $Plugin)
}
if ($Source) {
    $toolArguments += @("--source", $Source)
}
if ($UserChannelsOnly) {
    $toolArguments += "--user-channels-only"
}

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.link_titles_to_tmdb" -IntervalSeconds $IntervalSeconds -ToolArguments $toolArguments
