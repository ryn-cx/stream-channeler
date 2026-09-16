#!/bin/bash
# TODO: Validate

exec "$(dirname "${BASH_SOURCE[0]}")/_run_tool.sh" update_channels "$@"
