#!/usr/bin/env bash
# TODO: Validate

set -e
set -x

coverage run -m pytest tests/
coverage report
coverage html --title "${@-coverage}"
