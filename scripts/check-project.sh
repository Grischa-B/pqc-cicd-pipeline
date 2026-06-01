#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROFILES=("classical" "hybrid" "pqc")

echo "[check] PQC CI/CD Pipeline project check"
echo

echo "[check] 1/6 Validate profile configuration"
python3 -m unittest tests/test_profiles.py

echo
echo "[check] 2/6 Check required scripts"
required_scripts=(
  "scripts/build/build-images.sh"
  "scripts/certs/generate-certs.sh"
  "scripts/deploy/up.sh"
  "scripts/deploy/down.sh"
  "scripts/test/run-handshake-test.sh"
  "scripts/test/run-profile-tests.sh"
  "scripts/metrics/aggregate-results.py"
  "scripts/metrics/collect-runtime-metrics.py"
  "scripts/metrics/monitor-container-stats.py"
  "scripts/metrics/generate-combined-report.py"
  "scripts/metrics/generate-charts.py"
  "scripts/crypto/list-capabilities.sh"
  "scripts/run-pipeline.sh"
  "scripts/run-all.sh"
)

for script in "${required_scripts[@]}"; do
  if [[ ! -f "$script" ]]; then
    echo "[check] Missing script: $script" >&2
    exit 1
  fi

  if [[ ! -x "$script" ]]; then
    echo "[check] Script is not executable: $script" >&2
    exit 1
  fi

  echo "[check] OK: $script"
done

echo
echo "[check] 3/6 Check Docker images"
if ! docker image inspect pqc-crypto-base:local >/dev/null 2>&1; then
  echo "[check] Base image is missing, building images..."
  ./scripts/build/build-images.sh
else
  echo "[check] OK: pqc-crypto-base:local exists"
fi

echo
echo "[check] 4/6 Check OpenSSL/PQC capabilities"
./scripts/crypto/list-capabilities.sh | tee artifacts/reports/capabilities.txt

if ! grep -q "OpenSSL 3.5.6" artifacts/reports/capabilities.txt; then
  echo "[check] Expected OpenSSL 3.5.6 was not found in capabilities output." >&2
  exit 1
fi

if ! grep -q "X25519MLKEM768" artifacts/reports/capabilities.txt; then
  echo "[check] Expected X25519MLKEM768 was not found in capabilities output." >&2
  exit 1
fi

if ! grep -q "MLKEM768" artifacts/reports/capabilities.txt; then
  echo "[check] Expected MLKEM768 was not found in capabilities output." >&2
  exit 1
fi

echo
echo "[check] 5/6 Run all profiles"
./scripts/run-all.sh

echo
echo "[check] 6/6 Check report files"

required_reports=(
  "artifacts/reports/summary-all.md"
  "artifacts/reports/summary-all.csv"
  "artifacts/reports/summary-all.json"
  "artifacts/reports/charts/avg-handshake-ms.svg"
  "artifacts/reports/charts/handshake-range-ms.svg"
  "artifacts/reports/charts/total-pipeline-duration-ms.svg"
  "artifacts/reports/charts/test-stage-duration-ms.svg"
  "artifacts/reports/charts/cpu-max-percent.svg"
  "artifacts/reports/charts/memory-max-mib.svg"
  "artifacts/reports/charts/cert-chain-size-bytes.svg"
)

for profile in "${PROFILES[@]}"; do
  required_reports+=(
    "artifacts/reports/summary-${profile}.md"
    "artifacts/reports/summary-${profile}.csv"
    "artifacts/reports/summary-${profile}.json"
    "artifacts/metrics/raw-${profile}.csv"
  )
done

for file in "${required_reports[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[check] Missing report: $file" >&2
    exit 1
  fi

  echo "[check] OK: $file"
done

python3 -m json.tool artifacts/reports/summary-all.json >/dev/null

echo
echo "[check] Project check completed successfully."