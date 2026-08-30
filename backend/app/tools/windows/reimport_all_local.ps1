# TODO: Validate
# Re-import every show on the host, against the compose database.
#
# The same run as `import_queue_local.ps1` - the repo's own venv, the working
# tree as it is on disk, the database compose publishes - pointed at the reimport
# tool instead of the import queue. Every show the plugin user owns is updated with
# `force=True`, so nothing is skipped for being current and the run takes as long
# as the whole library does.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.reimport_all"
