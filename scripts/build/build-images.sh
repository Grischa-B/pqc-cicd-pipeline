#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

mkdir -p artifacts/reports artifacts/logs

VERSIONS_FILE="artifacts/reports/versions.txt"

{
  echo "=== Host tool versions ==="
  date -u +"timestamp_utc=%Y-%m-%dT%H:%M:%SZ"
  echo
  docker version
  echo
  docker compose version
  echo
} > "$VERSIONS_FILE" 2>&1 || true

echo "[build] Building base crypto image..."
docker build -t pqc-crypto-base:local -f docker/crypto/Dockerfile .

echo "[build] Building server/client images..."
docker compose build

{
  echo
  echo "=== Container OpenSSL version ==="
  docker run --rm pqc-crypto-base:local openssl version -a

  echo
  echo "=== Container OpenSSL providers ==="
  docker run --rm pqc-crypto-base:local openssl list -providers

  echo
  echo "=== Container OpenSSL KEM algorithms ==="
  docker run --rm pqc-crypto-base:local bash -lc 'openssl list -kem-algorithms 2>&1 || true'

  echo
  echo "=== Container OpenSSL key exchange algorithms ==="
  docker run --rm pqc-crypto-base:local bash -lc 'openssl list -key-exchange-algorithms 2>&1 || true'

  echo
  echo "=== Container OpenSSL TLS groups, if supported by list command ==="
  docker run --rm pqc-crypto-base:local bash -lc 'openssl list -tls-groups 2>&1 || true'

  echo
  echo "=== Container Python version ==="
  docker run --rm pqc-crypto-base:local python3 --version
} >> "$VERSIONS_FILE" 2>&1

echo "[build] Images built successfully."
echo "[build] Version report: $VERSIONS_FILE"