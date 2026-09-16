#!/bin/bash
# TODO: Validate

set -u

TOOL="${1:-}"
if [ -z "$TOOL" ]; then
  echo "Usage: $0 <tool_name> [tool args...]" >&2
  exit 1
fi
shift

SECRETS_FILE="${STREAM_CHANNELER_SECRETS:-$HOME/.config/stream-channeler/secrets.env}"
if [ ! -r "$SECRETS_FILE" ]; then
  echo "Missing secrets file $SECRETS_FILE." >&2
  exit 1
fi

set -a
. "$SECRETS_FILE"
set +a

cd "$(dirname "$0")/../../../.." || exit 1

git fetch --all
git reset --hard origin/master
git pull

TOOL="$TOOL" docker compose -f compose.tool.yml build tool

TOOL="$TOOL" docker compose -f compose.tool.yml run --rm \
  -v "$(pwd)/backend:/app/backend" tool \
  python -m "app.tools.$TOOL" "$@"
