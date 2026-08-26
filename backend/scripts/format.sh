#!/bin/sh -e
# TODO: Validate
set -x

ruff check app scripts --fix
ruff format app scripts
