#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

for profile in classical hybrid pqc; do
  echo "=== Running profile: $profile ==="
  ./scripts/run-pipeline.sh "$profile"
done