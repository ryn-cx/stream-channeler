#! /usr/bin/env bash
# TODO: Validate
set -e
set -x

python app/tests_pre_start.py

bash scripts/test.sh "$@"
