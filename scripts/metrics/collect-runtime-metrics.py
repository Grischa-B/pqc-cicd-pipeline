#!/usr/bin/env python3
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(command: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        return completed.returncode, completed.stdout.strip()
    except FileNotFoundError as exc:
        return 127, str(exc)


def safe_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0

    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def docker_image_id(image_name: str) -> str | None:
    rc, out = run_command(["docker", "image", "inspect", image_name, "--format", "{{.Id}}"])
    if rc != 0:
        return None
    return out or None


def read_container_stats(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def numeric_summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "avg": None,
            "max": None,
            "min": None,
        }

    return {
        "avg": round(sum(values) / len(values), 3),
        "max": round(max(values), 3),
        "min": round(min(values), 3),
    }


def aggregate_container_stats(path: Path) -> dict[str, Any]:
    rows = read_container_stats(path)

    cpu_values = [
        value
        for value in (safe_float(row.get("cpu_percent")) for row in rows)
        if value is not None
    ]

    memory_usage_values = [
        value
        for value in (safe_float(row.get("memory_usage_mib")) for row in rows)
        if value is not None
    ]

    memory_percent_values = [
        value
        for value in (safe_float(row.get("memory_percent")) for row in rows)
        if value is not None
    ]

    latest_net_io = None
    latest_block_io = None
    latest_pids = None

    if rows:
        latest_net_io = rows[-1].get("net_io")
        latest_block_io = rows[-1].get("block_io")
        latest_pids = rows[-1].get("pids")

    return {
        "container_stats_samples": len(rows),
        "server_cpu_percent": numeric_summary(cpu_values),
        "server_memory_usage_mib": numeric_summary(memory_usage_values),
        "server_memory_percent": numeric_summary(memory_percent_values),
        "server_net_io_latest": latest_net_io,
        "server_block_io_latest": latest_block_io,
        "server_pids_latest": latest_pids,
    }


def write_flat_csv(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    flat_data: dict[str, Any] = {}

    for key, value in data.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                flat_data[f"{key}_{nested_key}"] = nested_value
        else:
            flat_data[key] = value

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat_data.keys()))
        writer.writeheader()
        writer.writerow(flat_data)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: collect-runtime-metrics.py <profile>", file=sys.stderr)
        return 2

    profile = sys.argv[1]

    root = Path(__file__).resolve().parents[2]
    cert_dir = root / "artifacts" / "certs" / profile
    log_dir = root / "artifacts" / "logs" / profile
    reports_dir = root / "artifacts" / "reports"
    metrics_dir = root / "artifacts" / "metrics"
    container_stats_csv = metrics_dir / f"container-stats-{profile}.csv"

    reports_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    _, openssl_version = run_command([
        "docker",
        "run",
        "--rm",
        "pqc-crypto-base:local",
        "openssl",
        "version",
    ])

    _, python_version = run_command(["python3", "--version"])
    _, docker_version = run_command(["docker", "--version"])
    _, compose_version = run_command(["docker", "compose", "version"])

    ca_cert = cert_dir / "ca.crt"
    server_cert = cert_dir / "server.crt"
    server_key = cert_dir / "server.key"
    server_log = log_dir / "server.log"

    client_logs = sorted(log_dir.glob("client-*.log"))
    client_logs_total_size = sum(file_size(path) for path in client_logs)

    cert_chain_size = file_size(ca_cert) + file_size(server_cert)

    data: dict[str, Any] = {
        "profile": profile,
        "openssl_version": openssl_version,
        "python_version": python_version,
        "docker_version": docker_version,
        "docker_compose_version": compose_version,
        "crypto_image_id": docker_image_id("pqc-crypto-base:local"),
        "server_image_id": docker_image_id("pqc-tls-server:local"),
        "client_image_id": docker_image_id("pqc-tls-client:local"),
        "ca_cert_size_bytes": file_size(ca_cert),
        "server_cert_size_bytes": file_size(server_cert),
        "server_key_size_bytes": file_size(server_key),
        "cert_chain_size_bytes": cert_chain_size,
        "server_log_size_bytes": file_size(server_log),
        "client_logs_count": len(client_logs),
        "client_logs_total_size_bytes": client_logs_total_size,
        "profile_log_dir_size_bytes": directory_size(log_dir),
        "profile_cert_dir_size_bytes": directory_size(cert_dir),
    }

    data.update(aggregate_container_stats(container_stats_csv))

    json_path = reports_dir / f"runtime-{profile}.json"
    csv_path = metrics_dir / f"runtime-{profile}.csv"

    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_flat_csv(csv_path, data)

    print("[runtime-metrics] Runtime metrics written:")
    print(f"[runtime-metrics] - {json_path}")
    print(f"[runtime-metrics] - {csv_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())