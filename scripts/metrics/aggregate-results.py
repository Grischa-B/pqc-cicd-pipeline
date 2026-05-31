#!/usr/bin/env python3
import csv
import json
import statistics
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: aggregate-results.py <profile>", file=sys.stderr)
        return 2

    profile = sys.argv[1]

    root = Path(__file__).resolve().parents[2]
    raw_csv = root / "artifacts" / "metrics" / f"raw-{profile}.csv"
    cert_dir = root / "artifacts" / "certs" / profile
    reports_dir = root / "artifacts" / "reports"

    reports_dir.mkdir(parents=True, exist_ok=True)

    if not raw_csv.exists():
        print(f"[aggregate] Raw metrics not found: {raw_csv}", file=sys.stderr)
        return 1

    rows = []
    with raw_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    total = len(rows)
    successes = [r for r in rows if r.get("status") == "success"]
    failures = [r for r in rows if r.get("status") != "success"]

    times = []
    for row in successes:
        value = row.get("handshake_ms") or ""
        if value:
            times.append(float(value))

    errors = Counter((r.get("error") or "unknown").strip() for r in failures)

    key_file = cert_dir / "server.key"
    cert_file = cert_dir / "server.crt"
    ca_file = cert_dir / "ca.crt"

    summary = {
        "profile": profile,
        "total_runs": total,
        "successful_runs": len(successes),
        "failed_runs": len(failures),
        "success_rate": round(len(successes) / total, 4) if total else 0.0,
        "handshake_ms": {
            "avg": round(statistics.mean(times), 3) if times else None,
            "median": round(statistics.median(times), 3) if times else None,
            "min": round(min(times), 3) if times else None,
            "max": round(max(times), 3) if times else None,
        },
        "artifacts": {
            "server_key_size_bytes": key_file.stat().st_size if key_file.exists() else None,
            "server_cert_size_bytes": cert_file.stat().st_size if cert_file.exists() else None,
            "ca_cert_size_bytes": ca_file.stat().st_size if ca_file.exists() else None,
        },
        "errors": dict(errors),
    }

    json_path = reports_dir / f"summary-{profile}.json"
    md_path = reports_dir / f"summary-{profile}.md"
    csv_path = reports_dir / f"summary-{profile}.csv"

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "profile",
            "total_runs",
            "successful_runs",
            "failed_runs",
            "success_rate",
            "avg_handshake_ms",
            "median_handshake_ms",
            "min_handshake_ms",
            "max_handshake_ms",
            "server_key_size_bytes",
            "server_cert_size_bytes",
            "ca_cert_size_bytes",
        ])
        writer.writerow([
            summary["profile"],
            summary["total_runs"],
            summary["successful_runs"],
            summary["failed_runs"],
            summary["success_rate"],
            summary["handshake_ms"]["avg"],
            summary["handshake_ms"]["median"],
            summary["handshake_ms"]["min"],
            summary["handshake_ms"]["max"],
            summary["artifacts"]["server_key_size_bytes"],
            summary["artifacts"]["server_cert_size_bytes"],
            summary["artifacts"]["ca_cert_size_bytes"],
        ])

    md = []
    md.append(f"# Summary for profile `{profile}`")
    md.append("")
    md.append("| Metric | Value |")
    md.append("|---|---:|")
    md.append(f"| Total runs | {summary['total_runs']} |")
    md.append(f"| Successful runs | {summary['successful_runs']} |")
    md.append(f"| Failed runs | {summary['failed_runs']} |")
    md.append(f"| Success rate | {summary['success_rate']} |")
    md.append(f"| Average handshake, ms | {summary['handshake_ms']['avg']} |")
    md.append(f"| Median handshake, ms | {summary['handshake_ms']['median']} |")
    md.append(f"| Min handshake, ms | {summary['handshake_ms']['min']} |")
    md.append(f"| Max handshake, ms | {summary['handshake_ms']['max']} |")
    md.append(f"| Server key size, bytes | {summary['artifacts']['server_key_size_bytes']} |")
    md.append(f"| Server certificate size, bytes | {summary['artifacts']['server_cert_size_bytes']} |")
    md.append(f"| CA certificate size, bytes | {summary['artifacts']['ca_cert_size_bytes']} |")
    md.append("")

    if summary["errors"]:
        md.append("## Errors")
        md.append("")
        for error, count in summary["errors"].items():
            md.append(f"- `{error}`: {count}")

    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"[aggregate] Summary written:")
    print(f"[aggregate] - {json_path}")
    print(f"[aggregate] - {csv_path}")
    print(f"[aggregate] - {md_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())