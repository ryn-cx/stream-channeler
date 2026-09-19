# TODO: Validate
# Work out every unsettled title link on the host, against the compose database.
#
# The same run as `relink_episodes.ps1` - the repo's own venv, the working tree as
# it is on disk, the database compose publishes - pointed at the title relink tool.
# Nothing is imported; each non-canonical title is searched on TMDB again, and the
# canonical titles it stands for are set to what that search finds. A title a `User`
# has validated is left alone, a link they settled by hand is kept, and so is any
# link an episode they settled or validated still stands on.

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

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.relink_titles" -ToolArguments $toolArguments
