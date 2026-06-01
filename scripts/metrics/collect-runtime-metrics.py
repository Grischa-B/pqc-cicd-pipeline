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


def docker_stats(container_name: str) -> dict[str, str | None]:
    rc, out = run_command([
        "docker",
        "stats",
        "--no-stream",
        "--format",
        "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}",
        container_name,
    ])

    if rc != 0 or not out:
        return {
            "server_cpu_percent": None,
            "server_memory_usage": None,
            "server_memory_percent": None,
            "server_net_io": None,
            "server_block_io": None,
            "server_pids": None,
        }

    parts = [part.strip() for part in out.split(",", maxsplit=5)]
    while len(parts) < 6:
        parts.append(None)

    return {
        "server_cpu_percent": parts[0],
        "server_memory_usage": parts[1],
        "server_memory_percent": parts[2],
        "server_net_io": parts[3],
        "server_block_io": parts[4],
        "server_pids": parts[5],
    }


def write_flat_csv(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data.keys()))
        writer.writeheader()
        writer.writerow(data)


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

    data.update(docker_stats("pqc_tls_server"))

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