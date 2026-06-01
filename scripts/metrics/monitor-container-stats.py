#!/usr/bin/env python3
import csv
import re
import subprocess
import sys
import time
from pathlib import Path


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.returncode, completed.stdout.strip()


def parse_cpu_percent(value: str) -> float | None:
    value = value.strip().replace("%", "")
    try:
        return float(value)
    except ValueError:
        return None


def parse_memory_to_mib(value: str) -> float | None:
    value = value.strip()

    match = re.match(r"^([0-9.]+)\s*([A-Za-z]+)$", value)
    if not match:
        return None

    number = float(match.group(1))
    unit = match.group(2).lower()

    multipliers = {
        "b": 1 / (1024 * 1024),
        "kb": 1 / 1024,
        "kib": 1 / 1024,
        "mb": 1,
        "mib": 1,
        "gb": 1024,
        "gib": 1024,
    }

    multiplier = multipliers.get(unit)
    if multiplier is None:
        return None

    return number * multiplier


def parse_mem_usage(value: str) -> float | None:
    # Docker format example: "12.34MiB / 7.65GiB"
    used = value.split("/", maxsplit=1)[0].strip()
    return parse_memory_to_mib(used)


def collect_sample(container_name: str) -> dict[str, str | float | None]:
    rc, out = run_command([
        "docker",
        "stats",
        "--no-stream",
        "--format",
        "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}",
        container_name,
    ])

    timestamp = time.time()

    if rc != 0 or not out:
        return {
            "timestamp_unix": timestamp,
            "cpu_percent": None,
            "memory_usage_mib": None,
            "memory_percent": None,
            "net_io": None,
            "block_io": None,
            "pids": None,
        }

    parts = [part.strip() for part in out.split(",", maxsplit=5)]
    while len(parts) < 6:
        parts.append("")

    return {
        "timestamp_unix": timestamp,
        "cpu_percent": parse_cpu_percent(parts[0]),
        "memory_usage_mib": parse_mem_usage(parts[1]),
        "memory_percent": parse_cpu_percent(parts[2]),
        "net_io": parts[3],
        "block_io": parts[4],
        "pids": parts[5],
    }


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: monitor-container-stats.py <container-name> <output-csv> <interval-seconds>",
            file=sys.stderr,
        )
        return 2

    container_name = sys.argv[1]
    output_csv = Path(sys.argv[2])
    interval_seconds = float(sys.argv[3])

    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "timestamp_unix",
            "cpu_percent",
            "memory_usage_mib",
            "memory_percent",
            "net_io",
            "block_io",
            "pids",
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        while True:
            sample = collect_sample(container_name)
            writer.writerow(sample)
            f.flush()
            time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())