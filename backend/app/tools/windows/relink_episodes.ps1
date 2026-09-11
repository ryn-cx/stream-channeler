# TODO: Validate
# Work out every unsettled episode link on the host, against the compose database.
#
# The same run as `reimport_all_local.ps1` - the repo's own venv, the working tree
# as it is on disk, the database compose publishes - pointed at the relink tool.
# Nothing is imported; every non-canonical title is matched against the canonical
# titles it stands for again, leaving the episodes a `User` has validated and the
# links they settled by hand where they are.

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.relink_episodes"
