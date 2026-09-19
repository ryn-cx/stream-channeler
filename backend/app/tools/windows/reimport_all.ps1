# TODO: Validate
# Re-import every title on the host, against the compose database.
#
# The same run as `import_queue.ps1` - the repo's own venv, the working
# tree as it is on disk, the database compose publishes - pointed at the reimport
# tool instead of the import queue. Every title the plugin user owns is updated with
# `force=True`, so nothing is skipped for being current and the run takes as long
# as the whole library does.

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

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.reimport_all" -ToolArguments $toolArguments
