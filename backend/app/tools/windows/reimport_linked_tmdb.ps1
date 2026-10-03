# TODO: Validate
[CmdletBinding()]
param(
    [string[]]$Plugin,
    [string[]]$Source,
    [switch]$UserChannelsOnly,
    [int]$Threads = 1
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
$toolArguments += @("--threads", $Threads)

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.reimport_linked_tmdb" -ToolArguments $toolArguments
