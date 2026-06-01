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

SUMMARY_MD="artifacts/reports/summary-all.md"
SUMMARY_CSV="artifacts/reports/summary-all.csv"
SUMMARY_JSON="artifacts/reports/summary-all.json"

python3 - "$SUMMARY_MD" "$SUMMARY_CSV" "$SUMMARY_JSON" "${PROFILES[@]}" <<'PY'
import csv
import json
import sys
from pathlib import Path


summary_md = Path(sys.argv[1])
summary_csv = Path(sys.argv[2])
summary_json = Path(sys.argv[3])
profiles = sys.argv[4:]

reports_dir = Path("artifacts/reports")

rows = []

for profile in profiles:
    path = reports_dir / f"summary-{profile}.json"

    if not path.exists():
        raise SystemExit(f"[run-all] Missing summary: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    stage = data.get("stage_metrics", {})
    stage_durations = stage.get("duration_ms_by_stage", {})
    runtime = data.get("runtime_metrics", {})

    row = {
        "profile": data["profile"],
        "description": data["profile_config"]["description"],
        "tls_version_configured": data["profile_config"]["tls_version"],
        "key_exchange_group_configured": data["profile_config"]["key_exchange_group"],
        "signature_algorithm_configured": data["profile_config"]["signature_algorithm"],
        "total_runs": data["total_runs"],
        "successful_runs": data["successful_runs"],
        "failed_runs": data["failed_runs"],
        "success_rate": data["success_rate"],
        "avg_handshake_ms": data["handshake_ms"]["avg"],
        "median_handshake_ms": data["handshake_ms"]["median"],
        "min_handshake_ms": data["handshake_ms"]["min"],
        "max_handshake_ms": data["handshake_ms"]["max"],
        "total_pipeline_duration_ms": stage.get("total_pipeline_duration_ms"),
        "cert_generation_duration_ms": stage_durations.get("generate_certificates"),
        "test_duration_ms": stage_durations.get("run_integration_tests"),
        "report_generation_duration_ms": stage_durations.get("aggregate_results"),
        "dominant_expected_group": data["dominant_values"]["expected_group"],
        "dominant_actual_group": data["dominant_values"]["actual_group"],
        "dominant_group_evidence": data["dominant_values"]["group_evidence"],
        "dominant_tls_version_observed": data["dominant_values"]["tls_version"],
        "server_key_size_bytes": data["artifacts"]["server_key_size_bytes"],
        "server_cert_size_bytes": data["artifacts"]["server_cert_size_bytes"],
        "ca_cert_size_bytes": data["artifacts"]["ca_cert_size_bytes"],
        "cert_chain_size_bytes": runtime.get("cert_chain_size_bytes"),
        "server_log_size_bytes": runtime.get("server_log_size_bytes"),
        "client_logs_total_size_bytes": runtime.get("client_logs_total_size_bytes"),
        "profile_log_dir_size_bytes": runtime.get("profile_log_dir_size_bytes"),
        "container_stats_samples": runtime.get("container_stats_samples"),
        "server_cpu_avg_percent": (runtime.get("server_cpu_percent") or {}).get("avg"),
        "server_cpu_max_percent": (runtime.get("server_cpu_percent") or {}).get("max"),
        "server_memory_avg_mib": (runtime.get("server_memory_usage_mib") or {}).get("avg"),
        "server_memory_max_mib": (runtime.get("server_memory_usage_mib") or {}).get("max"),
        "server_memory_percent_avg": (runtime.get("server_memory_percent") or {}).get("avg"),
        "server_memory_percent_max": (runtime.get("server_memory_percent") or {}).get("max"),
        "server_net_io_latest": runtime.get("server_net_io_latest"),
        "openssl_version": runtime.get("openssl_version"),
        "crypto_image_id": runtime.get("crypto_image_id"),
    }

    rows.append(row)

combined = {
    "profiles": rows,
    "notes": [
        "The classical profile is the TLS 1.3 baseline with X25519 key exchange.",
        "The hybrid profile uses X25519MLKEM768 as a transition profile combining classical and post-quantum key establishment.",
        "The pqc profile is a maximum-supported PQC profile using MLKEM768 key exchange with a classical ECDSA certificate for TLS/X.509 stability.",
        "Stage duration metrics describe the CI/CD pipeline behavior rather than pure cryptographic primitive performance.",
        "Runtime resource metrics are collected as container snapshots and should be interpreted as engineering indicators.",
    ],
}

summary_json.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

fieldnames = list(rows[0].keys()) if rows else []

with summary_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

md_lines = []
md_lines.append("# PQC CI/CD Pipeline Experiment Summary")
md_lines.append("")
md_lines.append("## TLS handshake comparison")
md_lines.append("")
md_lines.append("| Profile | Successful / Total | Success rate | Avg handshake, ms | Median handshake, ms | Expected group | Actual group | TLS version |")
md_lines.append("|---|---:|---:|---:|---:|---|---|---|")

for row in rows:
    md_lines.append(
        f"| `{row['profile']}` | {row['successful_runs']} / {row['total_runs']} | "
        f"{row['success_rate']} | {row['avg_handshake_ms']} | {row['median_handshake_ms']} | "
        f"`{row['dominant_expected_group']}` | `{row['dominant_actual_group']}` | "
        f"`{row['dominant_tls_version_observed']}` |"
    )

md_lines.append("")
md_lines.append("## Pipeline stage duration")
md_lines.append("")
md_lines.append("| Profile | Total pipeline, ms | Cert generation, ms | Test stage, ms | Report generation, ms |")
md_lines.append("|---|---:|---:|---:|---:|")

for row in rows:
    md_lines.append(
        f"| `{row['profile']}` | {row['total_pipeline_duration_ms']} | "
        f"{row['cert_generation_duration_ms']} | {row['test_duration_ms']} | "
        f"{row['report_generation_duration_ms']} |"
    )

md_lines.append("")
md_lines.append("## Runtime and artifact metrics")
md_lines.append("")
md_lines.append("| Profile | CPU avg, % | CPU max, % | Memory avg, MiB | Memory max, MiB | Net I/O latest | Cert chain, bytes | Client logs, bytes |")
md_lines.append("|---|---:|---:|---:|---:|---|---:|---:|")

for row in rows:
    md_lines.append(
        f"| `{row['profile']}` | {row['server_cpu_avg_percent']} | "
        f"{row['server_cpu_max_percent']} | {row['server_memory_avg_mib']} | "
        f"{row['server_memory_max_mib']} | `{row['server_net_io_latest']}` | "
        f"{row['cert_chain_size_bytes']} | {row['client_logs_total_size_bytes']} |"
    )

md_lines.append("")
md_lines.append("## Notes")
md_lines.append("")

for note in combined["notes"]:
    md_lines.append(f"- {note}")

md_lines.append("")
md_lines.append("## Machine-readable outputs")
md_lines.append("")
md_lines.append("- `artifacts/reports/summary-all.json`")
md_lines.append("- `artifacts/reports/summary-all.csv`")

summary_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

print(f"[run-all] Combined Markdown report written to {summary_md}")
print(f"[run-all] Combined CSV report written to {summary_csv}")
print(f"[run-all] Combined JSON report written to {summary_json}")
PY

echo "[run-all] Combined reports generated successfully."