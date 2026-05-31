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
echo "[run-all] Building combined Markdown report..."

SUMMARY_ALL="artifacts/reports/summary-all.md"

{
  echo "# PQC CI/CD Pipeline Experiment Summary"
  echo
  echo "| Profile | Successful / Total | Success rate | Avg handshake, ms | Median handshake, ms | Expected group | Actual group | Group evidence | TLS version | Server cert, bytes | Server key, bytes |"
  echo "|---|---:|---:|---:|---:|---|---|---|---|---:|---:|"

  for profile in "${PROFILES[@]}"; do
    summary_json="artifacts/reports/summary-${profile}.json"

    if [[ ! -f "$summary_json" ]]; then
      echo "[run-all] Missing summary: $summary_json" >&2
      exit 1
    fi

    python3 - "$summary_json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))

profile = data["profile"]
successful = data["successful_runs"]
total = data["total_runs"]
success_rate = data["success_rate"]

handshake = data["handshake_ms"]
avg = handshake["avg"]
median = handshake["median"]

dominant = data["dominant_values"]
expected_group = dominant["expected_group"]
actual_group = dominant["actual_group"]
group_evidence = dominant["group_evidence"]
tls_version = dominant["tls_version"]

artifacts = data["artifacts"]
server_cert = artifacts["server_cert_size_bytes"]
server_key = artifacts["server_key_size_bytes"]

print(
    f"| `{profile}` | {successful} / {total} | {success_rate} | "
    f"{avg} | {median} | `{expected_group}` | `{actual_group}` | "
    f"`{group_evidence}` | `{tls_version}` | {server_cert} | {server_key} |"
)
PY
  done

  echo
  echo "## Notes"
  echo
  echo "- The classical profile is the TLS 1.3 baseline with X25519 key exchange."
  echo "- The hybrid profile uses X25519MLKEM768 as a transition profile combining classical and post-quantum key establishment."
  echo "- The pqc profile is a maximum-supported PQC profile using MLKEM768 key exchange with a classical ECDSA certificate for TLS/X.509 stability."
  echo "- Runtime keys, certificates, logs, metrics and reports are generated artifacts and are not intended to be committed to Git."
} > "$SUMMARY_ALL"

echo "[run-all] Combined report written to $SUMMARY_ALL"