# TODO: Validate
# Sort every title onto its plugin's channels on the host, against the compose database.
#
# The same run as `relink_episodes.ps1` - the repo's own venv, the working tree as
# it is on disk, the database compose publishes - pointed at the rechannel tool.
# Nothing is imported; each title is put into the queues of the channels the plugin
# sorts it into now, and the import queue is what fills those channels in.
#
# `-Plugin` and `-Source` narrow the run to one plugin, or to one of its sources,
# which is how a plugin that has just changed how it sorts is applied on its own.

[CmdletBinding()]
param(
    [string[]]$Plugin,
    [string[]]$Source
)

$ErrorActionPreference = "Stop"

$toolArguments = @()
if ($Plugin) {
    $toolArguments += @("--plugin", $Plugin)
}
if ($Source) {
    $toolArguments += @("--source", $Source)
}

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.rechannel" -ToolArguments $toolArguments
