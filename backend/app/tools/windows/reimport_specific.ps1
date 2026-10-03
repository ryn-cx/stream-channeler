# TODO: Validate
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$TitleId
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.reimport_specific" -ToolArguments $TitleId
