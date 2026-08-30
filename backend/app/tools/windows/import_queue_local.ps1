# TODO: Validate
# Run the import queue on the host, against the compose database.
#
# The simple counterpart of `run_import_queue.ps1`: no image build, no dependency
# dump, no container. The tool runs out of the repo's own venv, so the code it runs
# is the working tree as it is on disk and anything it writes into its dependencies
# stays there. Everything it talks to - the database, the plugins' APIs - is the
# same as the container run.
#
# The database is the one compose publishes, which `.env` gives the container as
# port 5432 (its own port inside the compose network) and the host as `DB_PORT`.
# Only the host port can be reached from here, so it is what gets used.
#
# It keeps running: once a pass finishes it waits `IntervalSeconds` and starts the
# next one. Ctrl-C stops it.

[CmdletBinding()]
param(
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "_run_tool.ps1") -Module "app.tools.import_queue" -IntervalSeconds $IntervalSeconds
