#!/bin/bash
# TODO: Validate

set -u

TOOL="${1:-}"
if [ -z "$TOOL" ]; then
  echo "Usage: $0 <tool_name> [tool args...]" >&2
  exit 1
fi
shift

CRED_DIR="${STREAM_CHANNELER_CRED_DIR:-/etc/stream-channeler/creds}"

# TODO: Validate
load_secret() {
  local secret_name="$1"
  local secret_file="$CRED_DIR/$secret_name.cred"
  local secret_value

  if [ ! -r "$secret_file" ]; then
    echo "Missing credential $secret_name ($secret_file)." >&2
    exit 1
  fi

  secret_value="$(systemd-creds decrypt --name="$secret_name" "$secret_file" -)" || {
    echo "Could not decrypt $secret_name. Is this running as root?" >&2
    exit 1
  }
  export "$secret_name=$secret_value"
}

for secret_name in \
  POSTGRES_USER \
  POSTGRES_PASSWORD \
  GET_AROUND_SERVER \
  YOUTUBE_API_KEY \
  WATCHMODE_API_KEY \
  CF_ACCESS_CLIENT_ID \
  CF_ACCESS_CLIENT_SECRET \
  TMDB_API_READ_TOKEN \
  PROXY; do
  load_secret "$secret_name"
done

cd ~/stream-channeler || exit 1

git fetch --all
git reset --hard origin/master
git pull

TOOL="$TOOL" docker compose -f compose.tool.yml build tool

TOOL="$TOOL" docker compose -f compose.tool.yml run --rm \
  -v "$(pwd)/backend:/app/backend" tool \
  python -m "app.tools.$TOOL" "$@"
