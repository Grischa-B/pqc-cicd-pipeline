#!/usr/bin/env python3
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any


def read_simple_yaml_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if ":" not in stripped:
            continue

        current_key, value = stripped.split(":", 1)
        if current_key.strip() == key:
            value = value.strip().strip('"').strip("'")
            return value or None

    return None


def safe_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def file_size(path: Path) -> int | None:
    return path.stat().st_size if path.exists() else None


def most_common_value(counter: Counter[str]) -> str | None:
    if not counter:
        return None

    return counter.most_common(1)[0][0]


def numeric_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "avg": None,
            "median": None,
            "min": None,
            "max": None,
        }

    return {
        "avg": round(statistics.mean(values), 3),
        "median": round(statistics.median(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
    }


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def parse_stage_metrics(path: Path) -> dict[str, Any]:
    rows = read_csv_rows(path)
    durations: dict[str, float | None] = {}
    statuses: dict[str, str] = {}
    exit_codes: dict[str, str] = {}

    for row in rows:
        stage = row.get("stage") or "unknown"
        durations[stage] = safe_float(row.get("duration_ms"))
        statuses[stage] = row.get("status") or "unknown"
        exit_codes[stage] = row.get("exit_code") or "unknown"

    return {
        "rows": rows,
        "duration_ms_by_stage": durations,
        "status_by_stage": statuses,
        "exit_code_by_stage": exit_codes,
        "total_pipeline_duration_ms": durations.get("total_pipeline"),
    }


def write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    runtime = summary["runtime_metrics"]
    stage = summary["stage_metrics"]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "profile",
            "description",
            "tls_version_configured",
            "key_exchange_group_configured",
            "signature_algorithm_configured",
            "total_runs",
            "successful_runs",
            "failed_runs",
            "success_rate",
            "avg_handshake_ms",
            "median_handshake_ms",
            "min_handshake_ms",
            "max_handshake_ms",
            "total_pipeline_duration_ms",
            "cert_generation_duration_ms",
            "test_duration_ms",
            "report_generation_duration_ms",
            "dominant_expected_group",
            "dominant_actual_group",
            "dominant_group_evidence",
            "dominant_tls_version_observed",
            "server_key_size_bytes",
            "server_cert_size_bytes",
            "ca_cert_size_bytes",
            "cert_chain_size_bytes",
            "server_log_size_bytes",
            "client_logs_total_size_bytes",
            "profile_log_dir_size_bytes",
            "server_cpu_percent",
            "server_memory_usage",
            "server_memory_percent",
            "server_net_io",
            "openssl_version",
            "crypto_image_id",
        ])

        writer.writerow([
            summary["profile"],
            summary["profile_config"]["description"],
            summary["profile_config"]["tls_version"],
            summary["profile_config"]["key_exchange_group"],
            summary["profile_config"]["signature_algorithm"],
            summary["total_runs"],
            summary["successful_runs"],
            summary["failed_runs"],
            summary["success_rate"],
            summary["handshake_ms"]["avg"],
            summary["handshake_ms"]["median"],
            summary["handshake_ms"]["min"],
            summary["handshake_ms"]["max"],
            stage["total_pipeline_duration_ms"],
            stage["duration_ms_by_stage"].get("generate_certificates"),
            stage["duration_ms_by_stage"].get("run_integration_tests"),
            stage["duration_ms_by_stage"].get("aggregate_results"),
            summary["dominant_values"]["expected_group"],
            summary["dominant_values"]["actual_group"],
            summary["dominant_values"]["group_evidence"],
            summary["dominant_values"]["tls_version"],
            summary["artifacts"]["server_key_size_bytes"],
            summary["artifacts"]["server_cert_size_bytes"],
            summary["artifacts"]["ca_cert_size_bytes"],
            runtime.get("cert_chain_size_bytes"),
            runtime.get("server_log_size_bytes"),
            runtime.get("client_logs_total_size_bytes"),
            runtime.get("profile_log_dir_size_bytes"),
            runtime.get("server_cpu_percent"),
            runtime.get("server_memory_usage"),
            runtime.get("server_memory_percent"),
            runtime.get("server_net_io"),
            runtime.get("openssl_version"),
            runtime.get("crypto_image_id"),
        ])


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    runtime = summary["runtime_metrics"]
    stage = summary["stage_metrics"]
    profile = summary["profile"]

    lines: list[str] = []

    lines.append(f"# Summary for profile `{profile}`")
    lines.append("")
    lines.append("## Profile configuration")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Description | {summary['profile_config']['description']} |")
    lines.append(f"| Configured TLS version | `{summary['profile_config']['tls_version']}` |")
    lines.append(f"| Configured key exchange group | `{summary['profile_config']['key_exchange_group']}` |")
    lines.append(f"| Configured signature algorithm | `{summary['profile_config']['signature_algorithm']}` |")
    lines.append("")
    lines.append("## Test result")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total runs | {summary['total_runs']} |")
    lines.append(f"| Successful runs | {summary['successful_runs']} |")
    lines.append(f"| Failed runs | {summary['failed_runs']} |")
    lines.append(f"| Success rate | {summary['success_rate']} |")
    lines.append(f"| Average handshake, ms | {summary['handshake_ms']['avg']} |")
    lines.append(f"| Median handshake, ms | {summary['handshake_ms']['median']} |")
    lines.append(f"| Min handshake, ms | {summary['handshake_ms']['min']} |")
    lines.append(f"| Max handshake, ms | {summary['handshake_ms']['max']} |")
    lines.append("")
    lines.append("## Pipeline stage duration")
    lines.append("")
    lines.append("| Stage | Status | Duration, ms |")
    lines.append("|---|---|---:|")

    for row in stage["rows"]:
        lines.append(
            f"| `{row.get('stage')}` | `{row.get('status')}` | {row.get('duration_ms')} |"
        )

    lines.append("")
    lines.append("## Cryptographic verification")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Dominant expected group | `{summary['dominant_values']['expected_group']}` |")
    lines.append(f"| Dominant actual group | `{summary['dominant_values']['actual_group']}` |")
    lines.append(f"| Dominant group evidence | `{summary['dominant_values']['group_evidence']}` |")
    lines.append(f"| Dominant observed TLS version | `{summary['dominant_values']['tls_version']}` |")
    lines.append(f"| OpenSSL exit codes | `{summary['distributions']['openssl_exit_codes']}` |")
    lines.append("")
    lines.append("## Runtime and resource metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| OpenSSL version | `{runtime.get('openssl_version')}` |")
    lines.append(f"| Docker image ID | `{runtime.get('crypto_image_id')}` |")
    lines.append(f"| Server CPU percent snapshot | `{runtime.get('server_cpu_percent')}` |")
    lines.append(f"| Server memory usage snapshot | `{runtime.get('server_memory_usage')}` |")
    lines.append(f"| Server memory percent snapshot | `{runtime.get('server_memory_percent')}` |")
    lines.append(f"| Server network I/O snapshot | `{runtime.get('server_net_io')}` |")
    lines.append(f"| Server log size, bytes | {runtime.get('server_log_size_bytes')} |")
    lines.append(f"| Client logs total size, bytes | {runtime.get('client_logs_total_size_bytes')} |")
    lines.append(f"| Profile log directory size, bytes | {runtime.get('profile_log_dir_size_bytes')} |")
    lines.append("")
    lines.append("## Artifact sizes")
    lines.append("")
    lines.append("| Artifact | Size, bytes |")
    lines.append("|---|---:|")
    lines.append(f"| Server key | {summary['artifacts']['server_key_size_bytes']} |")
    lines.append(f"| Server certificate | {summary['artifacts']['server_cert_size_bytes']} |")
    lines.append(f"| CA certificate | {summary['artifacts']['ca_cert_size_bytes']} |")
    lines.append(f"| Certificate chain | {runtime.get('cert_chain_size_bytes')} |")
    lines.append("")
    lines.append("## Distributions")
    lines.append("")
    lines.append("| Field | Distribution |")
    lines.append("|---|---|")
    lines.append(f"| Status | `{summary['distributions']['statuses']}` |")
    lines.append(f"| Expected group | `{summary['distributions']['expected_groups']}` |")
    lines.append(f"| Actual group | `{summary['distributions']['actual_groups']}` |")
    lines.append(f"| Group evidence | `{summary['distributions']['group_evidence']}` |")
    lines.append(f"| TLS version | `{summary['distributions']['tls_versions']}` |")
    lines.append("")

    if summary["errors"]:
        lines.append("## Errors")
        lines.append("")
        for error, count in summary["errors"].items():
            lines.append(f"- `{error}`: {count}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: aggregate-results.py <profile>", file=sys.stderr)
        return 2

    profile = sys.argv[1]

    root = Path(__file__).resolve().parents[2]
    raw_csv = root / "artifacts" / "metrics" / f"raw-{profile}.csv"
    stages_csv = root / "artifacts" / "metrics" / f"stages-{profile}.csv"
    runtime_json = root / "artifacts" / "reports" / f"runtime-{profile}.json"
    cert_dir = root / "artifacts" / "certs" / profile
    reports_dir = root / "artifacts" / "reports"
    profile_file = root / "configs" / "profiles" / f"{profile}.yml"

    reports_dir.mkdir(parents=True, exist_ok=True)

    if not raw_csv.exists():
        print(f"[aggregate] Raw metrics not found: {raw_csv}", file=sys.stderr)
        return 1

    rows = read_csv_rows(raw_csv)

    total = len(rows)
    successes = [r for r in rows if r.get("status") == "success"]
    failures = [r for r in rows if r.get("status") != "success"]

    times = [
        parsed
        for parsed in (safe_float(row.get("handshake_ms")) for row in successes)
        if parsed is not None
    ]

    statuses = Counter(row.get("status") or "unknown" for row in rows)
    expected_groups = Counter(row.get("expected_group") or "unknown" for row in rows)
    actual_groups = Counter(row.get("actual_group") or "unknown" for row in rows)
    group_evidence = Counter(row.get("group_evidence") or "unknown" for row in rows)
    tls_versions = Counter(row.get("tls_version") or "unknown" for row in rows)
    openssl_exit_codes = Counter(row.get("openssl_exit_code") or "unknown" for row in rows)

    errors = Counter((r.get("error") or "unknown").strip() for r in failures)

    key_file = cert_dir / "server.key"
    cert_file = cert_dir / "server.crt"
    ca_file = cert_dir / "ca.crt"

    summary: dict[str, Any] = {
        "profile": profile,
        "profile_config": {
            "description": read_simple_yaml_value(profile_file, "description"),
            "tls_version": read_simple_yaml_value(profile_file, "tls_version"),
            "key_exchange_group": read_simple_yaml_value(profile_file, "key_exchange_group"),
            "signature_algorithm": read_simple_yaml_value(profile_file, "signature_algorithm"),
        },
        "total_runs": total,
        "successful_runs": len(successes),
        "failed_runs": len(failures),
        "success_rate": round(len(successes) / total, 4) if total else 0.0,
        "handshake_ms": numeric_summary(times),
        "dominant_values": {
            "expected_group": most_common_value(expected_groups),
            "actual_group": most_common_value(actual_groups),
            "group_evidence": most_common_value(group_evidence),
            "tls_version": most_common_value(tls_versions),
        },
        "distributions": {
            "statuses": dict(statuses),
            "expected_groups": dict(expected_groups),
            "actual_groups": dict(actual_groups),
            "group_evidence": dict(group_evidence),
            "tls_versions": dict(tls_versions),
            "openssl_exit_codes": dict(openssl_exit_codes),
        },
        "stage_metrics": parse_stage_metrics(stages_csv),
        "runtime_metrics": read_json_object(runtime_json),
        "artifacts": {
            "server_key_size_bytes": file_size(key_file),
            "server_cert_size_bytes": file_size(cert_file),
            "ca_cert_size_bytes": file_size(ca_file),
        },
        "errors": dict(errors),
    }

    json_path = reports_dir / f"summary-{profile}.json"
    md_path = reports_dir / f"summary-{profile}.md"
    csv_path = reports_dir / f"summary-{profile}.csv"

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_summary_csv(csv_path, summary)
    write_summary_md(md_path, summary)

    print("[aggregate] Summary written:")
    print(f"[aggregate] - {json_path}")
    print(f"[aggregate] - {csv_path}")
    print(f"[aggregate] - {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())