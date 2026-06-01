#!/usr/bin/env python3
import csv
import json
import sys
from pathlib import Path
from typing import Any


def load_profile_summary(reports_dir: Path, profile: str) -> dict[str, Any]:
    path = reports_dir / f"summary-{profile}.json"

    if not path.exists():
        raise FileNotFoundError(f"Missing summary: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def build_row(data: dict[str, Any]) -> dict[str, Any]:
    stage = data.get("stage_metrics", {})
    stage_durations = stage.get("duration_ms_by_stage", {})
    runtime = data.get("runtime_metrics", {})

    return {
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


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    combined = {
        "profiles": rows,
        "notes": [
            "The classical profile is the TLS 1.3 baseline with X25519 key exchange.",
            "The hybrid profile uses X25519MLKEM768 as a transition profile combining classical and post-quantum key establishment.",
            "The pqc profile is a maximum-supported PQC profile using MLKEM768 key exchange with a classical ECDSA certificate for TLS/X.509 stability.",
            "Stage duration metrics describe the CI/CD pipeline behavior rather than pure cryptographic primitive performance.",
            "Runtime resource metrics are collected as container samples and should be interpreted as engineering indicators.",
        ],
    }

    path.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else []

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    md_lines: list[str] = []

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
    md_lines.append("## Charts")
    md_lines.append("")
    md_lines.append("- [Average TLS handshake time](charts/avg-handshake-ms.svg)")
    md_lines.append("- [TLS handshake time range](charts/handshake-range-ms.svg)")
    md_lines.append("- [Total pipeline duration](charts/total-pipeline-duration-ms.svg)")
    md_lines.append("- [Integration test stage duration](charts/test-stage-duration-ms.svg)")
    md_lines.append("- [Maximum server CPU usage](charts/cpu-max-percent.svg)")
    md_lines.append("- [Maximum server memory usage](charts/memory-max-mib.svg)")
    md_lines.append("- [Certificate chain size](charts/cert-chain-size-bytes.svg)")
    md_lines.append("")
    md_lines.append("## Notes")
    md_lines.append("")
    md_lines.append("- The classical profile is the TLS 1.3 baseline with X25519 key exchange.")
    md_lines.append("- The hybrid profile uses X25519MLKEM768 as a transition profile combining classical and post-quantum key establishment.")
    md_lines.append("- The pqc profile is a maximum-supported PQC profile using MLKEM768 key exchange with a classical ECDSA certificate for TLS/X.509 stability.")
    md_lines.append("- Stage duration metrics describe the CI/CD pipeline behavior rather than pure cryptographic primitive performance.")
    md_lines.append("- Runtime resource metrics are collected as container samples and should be interpreted as engineering indicators.")
    md_lines.append("")
    md_lines.append("## Machine-readable outputs")
    md_lines.append("")
    md_lines.append("- `artifacts/reports/summary-all.json`")
    md_lines.append("- `artifacts/reports/summary-all.csv`")

    path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: generate-combined-report.py <profile> [<profile> ...]", file=sys.stderr)
        return 2

    profiles = sys.argv[1:]

    root = Path(__file__).resolve().parents[2]
    reports_dir = root / "artifacts" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    rows = [
        build_row(load_profile_summary(reports_dir, profile))
        for profile in profiles
    ]

    summary_md = reports_dir / "summary-all.md"
    summary_csv = reports_dir / "summary-all.csv"
    summary_json = reports_dir / "summary-all.json"

    write_json(summary_json, rows)
    write_csv(summary_csv, rows)
    write_markdown(summary_md, rows)

    print(f"[combined-report] Markdown report written to {summary_md}")
    print(f"[combined-report] CSV report written to {summary_csv}")
    print(f"[combined-report] JSON report written to {summary_json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())