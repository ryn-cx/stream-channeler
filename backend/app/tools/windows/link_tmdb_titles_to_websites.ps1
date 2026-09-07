# TODO: Validate
[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.link_tmdb_titles_to_websites" -IntervalSeconds $IntervalSeconds
