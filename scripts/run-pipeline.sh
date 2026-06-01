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
  artifacts/reports

STAGES_CSV="artifacts/metrics/stages-${PROFILE}.csv"

echo "profile,stage,status,duration_ms,started_at_utc,finished_at_utc,exit_code" > "$STAGES_CSV"

now_utc() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

now_ns() {
  date +%s%N
}

duration_ms() {
  local start_ns="$1"
  local end_ns="$2"

  awk "BEGIN { printf \"%.3f\", (${end_ns} - ${start_ns}) / 1000000 }"
}

write_stage_metric() {
  local stage="$1"
  local status="$2"
  local duration="$3"
  local started_at="$4"
  local finished_at="$5"
  local exit_code="$6"

  printf "%s,%s,%s,%s,%s,%s,%s\n" \
    "$PROFILE" \
    "$stage" \
    "$status" \
    "$duration" \
    "$started_at" \
    "$finished_at" \
    "$exit_code" >> "$STAGES_CSV"
}

image_exists() {
  docker image inspect "$1" >/dev/null 2>&1
}

stage_verify_docker_images() {
  if [[ "${FORCE_REBUILD:-0}" == "1" ]]; then
    echo "[pipeline] FORCE_REBUILD=1, rebuilding images..."
    ./scripts/build/build-images.sh
  elif image_exists "pqc-crypto-base:local" && image_exists "pqc-tls-server:local" && image_exists "pqc-tls-client:local"; then
    echo "[pipeline] Docker images already exist, skipping rebuild."
    echo "[pipeline] To force rebuild, run: FORCE_REBUILD=1 ./scripts/run-pipeline.sh $PROFILE"
  else
    echo "[pipeline] Some Docker images are missing, building images..."
    ./scripts/build/build-images.sh
  fi
}

stage_generate_certificates() {
  ./scripts/certs/generate-certs.sh "$PROFILE"
}

stage_stop_previous_environment() {
  ./scripts/deploy/down.sh >/dev/null 2>&1 || true
}

stage_start_tls_server() {
  ./scripts/deploy/up.sh "$PROFILE"
}

stage_run_integration_tests() {
  local stats_csv="artifacts/metrics/container-stats-${PROFILE}.csv"
  local monitor_pid=""

  rm -f "$stats_csv"

  echo "[pipeline] Starting container stats monitor: $stats_csv"

  python3 scripts/metrics/monitor-container-stats.py \
    "pqc_tls_server" \
    "$stats_csv" \
    "0.2" &
  monitor_pid="$!"

  set +e
  ./scripts/test/run-profile-tests.sh "$PROFILE"
  local test_rc=$?
  set -e

  if [[ -n "$monitor_pid" ]]; then
    kill "$monitor_pid" >/dev/null 2>&1 || true
    wait "$monitor_pid" >/dev/null 2>&1 || true
  fi

  echo "[pipeline] Container stats saved to: $stats_csv"

  return "$test_rc"
}

stage_collect_runtime_metrics() {
  python3 scripts/metrics/collect-runtime-metrics.py "$PROFILE"
}

stage_aggregate_results() {
  python3 scripts/metrics/aggregate-results.py "$PROFILE"
}

run_stage() {
  local stage="$1"
  shift

  local started_at
  local finished_at
  local start_ns
  local end_ns
  local duration
  local rc

  echo "[pipeline] Stage: $stage"

  started_at="$(now_utc)"
  start_ns="$(now_ns)"

  set +e
  "$@"
  rc=$?
  set -e

  end_ns="$(now_ns)"
  finished_at="$(now_utc)"
  duration="$(duration_ms "$start_ns" "$end_ns")"

  if [[ "$rc" -eq 0 ]]; then
    write_stage_metric "$stage" "success" "$duration" "$started_at" "$finished_at" "$rc"
    echo "[pipeline] Stage completed: $stage duration_ms=$duration"
  else
    write_stage_metric "$stage" "failed" "$duration" "$started_at" "$finished_at" "$rc"
    echo "[pipeline] Stage failed: $stage duration_ms=$duration exit_code=$rc" >&2
    exit "$rc"
  fi
}

cleanup() {
  echo "[pipeline] Cleaning up Docker Compose environment..."
  ./scripts/deploy/down.sh >/dev/null 2>&1 || true
}

trap cleanup EXIT

PIPELINE_STARTED_AT="$(now_utc)"
PIPELINE_START_NS="$(now_ns)"

echo "[pipeline] Running profile: $PROFILE"
echo "[pipeline] Stage metrics: $STAGES_CSV"

run_stage "verify_docker_images" stage_verify_docker_images
run_stage "generate_certificates" stage_generate_certificates
run_stage "stop_previous_environment" stage_stop_previous_environment
run_stage "start_tls_server" stage_start_tls_server
run_stage "run_integration_tests" stage_run_integration_tests
run_stage "collect_runtime_metrics" stage_collect_runtime_metrics
run_stage "aggregate_results" stage_aggregate_results

PIPELINE_END_NS="$(now_ns)"
PIPELINE_FINISHED_AT="$(now_utc)"
PIPELINE_DURATION_MS="$(duration_ms "$PIPELINE_START_NS" "$PIPELINE_END_NS")"

write_stage_metric \
  "total_pipeline" \
  "success" \
  "$PIPELINE_DURATION_MS" \
  "$PIPELINE_STARTED_AT" \
  "$PIPELINE_FINISHED_AT" \
  "0"

echo "[pipeline] Refreshing final profile summary with complete stage metrics..."
python3 scripts/metrics/aggregate-results.py "$PROFILE"

echo "[pipeline] Profile completed successfully: $PROFILE"
echo "[pipeline] Total duration, ms: $PIPELINE_DURATION_MS"