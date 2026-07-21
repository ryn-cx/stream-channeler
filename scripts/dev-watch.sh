#! /usr/bin/env bash

# Bring the local dev stack up with keyring secrets and watch for source changes.
#
# Same keyring-sourced secrets as dev-up.sh (see scripts/load-secrets.sh).
# `watch` builds, starts, then syncs/rebuilds services per their compose
# `develop.watch` blocks, so backend edits hot-reload and frontend edits rebuild.
# Runs in the foreground streaming sync/rebuild logs. Pass service names to scope
# it, e.g. `scripts/dev-watch.sh backend`.

set -e

cd "$(dirname "$0")/.."

source scripts/load-secrets.sh

docker compose --env-file .env watch "$@"
