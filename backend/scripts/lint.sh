#!/usr/bin/env bash
# TODO: Validate

set -e
set -x

mypy app
ty check app
ruff check app
ruff format app --check
