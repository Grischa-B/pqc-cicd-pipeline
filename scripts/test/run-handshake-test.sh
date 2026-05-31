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
  echo "[test] Profile not found: $PROFILE_FILE" >&2
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
EXPECTED_GROUP="$(yaml_value "group" "$PROFILE_FILE")"
REPEATS="$(yaml_value "repeats" "$PROFILE_FILE")"
TIMEOUT_SECONDS="$(yaml_value "timeout_seconds" "$PROFILE_FILE")"

if [[ -z "$TLS_GROUP" ]]; then TLS_GROUP="$EXPECTED_GROUP"; fi
if [[ -z "$EXPECTED_GROUP" ]]; then EXPECTED_GROUP="$TLS_GROUP"; fi
if [[ -z "$REPEATS" ]]; then REPEATS="1"; fi
if [[ -z "$TIMEOUT_SECONDS" ]]; then TIMEOUT_SECONDS="10"; fi

cd "$ROOT_DIR"

mkdir -p "artifacts/logs/${PROFILE}" "artifacts/metrics"

RAW_CSV="artifacts/metrics/raw-${PROFILE}.csv"

echo "profile,iteration,status,handshake_ms,expected_group,actual_group,error" > "$RAW_CSV"

echo "[test] Running TLS handshakes: profile=$PROFILE repeats=$REPEATS expected_group=$EXPECTED_GROUP"

docker compose run -T --rm --no-deps \
  -e PROFILE="$PROFILE" \
  -e TLS_GROUP="$TLS_GROUP" \
  -e EXPECTED_GROUP="$EXPECTED_GROUP" \
  -e REPEATS="$REPEATS" \
  -e TIMEOUT_SECONDS="$TIMEOUT_SECONDS" \
  tls-client bash -s <<'CONTAINER_SCRIPT'
set -euo pipefail

CERT_DIR="/artifacts/certs/${PROFILE}"
LOG_DIR="/artifacts/logs/${PROFILE}"
RAW_CSV="/artifacts/metrics/raw-${PROFILE}.csv"

mkdir -p "$LOG_DIR"

csv_escape() {
  local value="${1:-}"
  value="${value//$'\n'/ }"
  value="${value//$'\r'/ }"
  value="${value//\"/\"\"}"
  printf '"%s"' "$value"
}

for i in $(seq 1 "$REPEATS"); do
  LOG_FILE="$LOG_DIR/client-${i}.log"

  start_ns="$(date +%s%N)"

  set +e
  timeout "$TIMEOUT_SECONDS" openssl s_client \
    -connect tls-server:8443 \
    -servername localhost \
    -tls1_3 \
    -groups "$TLS_GROUP" \
    -CAfile "$CERT_DIR/ca.crt" \
    -verify_return_error \
    < /dev/null > "$LOG_FILE" 2>&1
  rc=$?
  set -e

  end_ns="$(date +%s%N)"
  handshake_ms="$(awk "BEGIN { printf \"%.3f\", (${end_ns} - ${start_ns}) / 1000000 }")"

  actual_group="$(grep -m 1 "Server Temp Key:" "$LOG_FILE" | sed -E "s/.*Server Temp Key: ([^, ]+).*/\1/" || true)"

  if [[ -z "$actual_group" ]]; then
    actual_group="unknown"
  fi

  if [[ "$rc" -eq 0 ]]; then
    status="success"
    error=""
  else
    status="failed"
    error="$(tail -n 5 "$LOG_FILE" | tr '\n' ' ' || true)"
  fi

  if [[ "$status" == "success" && "$actual_group" != "$EXPECTED_GROUP" ]]; then
    status="failed"
    error="expected group ${EXPECTED_GROUP}, got ${actual_group}"
  fi

  {
    printf "%s,%s,%s,%s,%s,%s," \
      "$PROFILE" \
      "$i" \
      "$status" \
      "$handshake_ms" \
      "$EXPECTED_GROUP" \
      "$actual_group"
    csv_escape "$error"
    printf "\n"
  } >> "$RAW_CSV"

  echo "[test] iteration=$i status=$status handshake_ms=$handshake_ms actual_group=$actual_group"

  if [[ "$status" != "success" ]]; then
    echo "[test] failed iteration log: $LOG_FILE" >&2
  fi
done
CONTAINER_SCRIPT

echo "[test] Raw metrics saved to $RAW_CSV"

TOTAL_COUNT="$(awk 'NR > 1 { c++ } END { print c + 0 }' "$RAW_CSV")"
FAILED_COUNT="$(awk -F',' 'NR > 1 && $3 != "success" { c++ } END { print c + 0 }' "$RAW_CSV")"

if [[ "$TOTAL_COUNT" -eq 0 ]]; then
  echo "[test] No handshake test rows were produced." >&2
  exit 1
fi

if [[ "$FAILED_COUNT" -ne 0 ]]; then
  echo "[test] Failed handshakes: $FAILED_COUNT" >&2
  exit 1
fi

echo "[test] All handshakes completed successfully. total=$TOTAL_COUNT"