#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROFILES=("classical" "hybrid" "pqc")

mkdir -p artifacts/reports

echo "[run-all] Running all profiles: ${PROFILES[*]}"

for profile in "${PROFILES[@]}"; do
  echo
  echo "=== Running profile: $profile ==="
  ./scripts/run-pipeline.sh "$profile"
done

echo
echo "[run-all] Building combined reports..."
python3 scripts/metrics/generate-combined-report.py "${PROFILES[@]}"

echo
echo "[run-all] Building charts..."
python3 scripts/metrics/generate-charts.py

echo "[run-all] Combined reports and charts generated successfully."