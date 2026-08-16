#! /usr/bin/env bash

# Read dev secrets from the OS keyring (the same store the host app uses) and
# export them so Compose substitutes them into the containers. Keeps real secrets
# out of any tracked file. Sourced by dev-up.sh and dev-watch.sh; run from the
# repo root.

if [ -x .venv/Scripts/keyring.exe ]; then
  keyring_bin=.venv/Scripts/keyring.exe
else
  keyring_bin=.venv/bin/keyring
fi

for secret_name in \
  GET_AROUND_SERVER \
  CF_ACCESS_CLIENT_ID \
  CF_ACCESS_CLIENT_SECRET \
  TMDB_API_READ_TOKEN \
  WATCHMODE_API_KEY; do
  export "$secret_name=$("$keyring_bin" get get-around "$secret_name")"
done
