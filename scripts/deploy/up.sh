#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <profile>" >&2
  exit 2
fi

PROFILE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROFILE_FILE="$ROOT_DIR/configs/profiles/${PROFILE}.yml"

if [[ ! -f "$PROFILE_FILE" ]]; then
  echo "[deploy] Profile not found: $PROFILE_FILE" >&2
  exit 1
fi

yaml_value() {
  local key="$1"
  local file="$2"

  awk -F': *' -v key="$key" '
    {
      k=$1
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
      if (k == key) {
        v=$2
        gsub(/^[[:space:]"]+|[[:space:]"]+$/, "", v)
        print v
        exit
      }
    }
  ' "$file"
}

TLS_GROUP="$(yaml_value "key_exchange_group" "$PROFILE_FILE")"

if [[ -z "$TLS_GROUP" ]]; then
  echo "[deploy] key_exchange_group is empty in $PROFILE_FILE" >&2
  exit 1
fi

cd "$ROOT_DIR"

mkdir -p "artifacts/logs/${PROFILE}"

echo "[deploy] Starting TLS server for profile=$PROFILE group=$TLS_GROUP"

PROFILE="$PROFILE" TLS_GROUP="$TLS_GROUP" docker compose up -d tls-server

echo "[deploy] Waiting for TLS server to become ready..."

for i in $(seq 1 30); do
  if docker logs pqc_tls_server 2>&1 | grep -q "ACCEPT"; then
    echo "[deploy] TLS server is ready."
    docker compose ps
    exit 0
  fi

  if ! docker ps --format '{{.Names}}' | grep -qx 'pqc_tls_server'; then
    echo "[deploy] TLS server container is not running." >&2
    docker logs pqc_tls_server || true
    exit 1
  fi

  sleep 1
done

echo "[deploy] TLS server did not become ready in time." >&2
docker logs pqc_tls_server || true
exit 1