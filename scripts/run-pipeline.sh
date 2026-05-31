#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <profile>" >&2
  echo "Example: $0 classical" >&2
  exit 2
fi

PROFILE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE_FILE="$ROOT_DIR/configs/profiles/${PROFILE}.yml"

if [[ ! -f "$PROFILE_FILE" ]]; then
  echo "[pipeline] Profile not found: $PROFILE_FILE" >&2
  exit 1
fi

cd "$ROOT_DIR"

mkdir -p \
  artifacts/certs \
  artifacts/logs \
  artifacts/metrics \
  artifacts/reports \
  results

cleanup() {
  echo "[pipeline] Cleaning up Docker Compose environment..."
  ./scripts/deploy/down.sh >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "[pipeline] Running profile: $PROFILE"

echo "[pipeline] Stage 1/6: build images"
./scripts/build/build-images.sh

echo "[pipeline] Stage 2/6: generate certificates"
./scripts/certs/generate-certs.sh "$PROFILE"

echo "[pipeline] Stage 3/6: stop previous environment if any"
./scripts/deploy/down.sh >/dev/null 2>&1 || true

echo "[pipeline] Stage 4/6: start TLS server"
./scripts/deploy/up.sh "$PROFILE"

echo "[pipeline] Stage 5/6: run integration tests"
./scripts/test/run-profile-tests.sh "$PROFILE"

echo "[pipeline] Stage 6/6: aggregate results"
python3 scripts/metrics/aggregate-results.py "$PROFILE"

echo "[pipeline] Profile completed successfully: $PROFILE"