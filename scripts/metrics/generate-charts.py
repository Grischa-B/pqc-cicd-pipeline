#!/usr/bin/env python3
import csv
import html
import sys
from pathlib import Path
from typing import Any


PROFILE_LABELS = {
    "classical": "classical",
    "hybrid": "hybrid",
    "pqc": "pqc",
}


def safe_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def read_summary_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Summary CSV not found: {path}")

    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def format_value(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"

    if abs(value) >= 100:
        return f"{value:.1f}{unit}"

    return f"{value:.3g}{unit}"


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>',
        'text { font-family: Arial, sans-serif; fill: #222; }',
        '.title { font-size: 20px; font-weight: bold; }',
        '.subtitle { font-size: 12px; fill: #555; }',
        '.axis { stroke: #333; stroke-width: 1; }',
        '.grid { stroke: #ddd; stroke-width: 1; }',
        '.bar { fill: #4f81bd; }',
        '.bar-alt { fill: #9bbb59; }',
        '.label { font-size: 12px; }',
        '.tick { font-size: 11px; fill: #555; }',
        '.value { font-size: 12px; font-weight: bold; }',
        '.range { stroke: #4f81bd; stroke-width: 3; }',
        '.dot { fill: #c0504d; }',
        '.dot-alt { fill: #4f81bd; }',
        '</style>',
    ]


def write_svg(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def bar_chart(
    rows: list[dict[str, str]],
    metric_key: str,
    output_path: Path,
    title: str,
    y_label: str,
    unit: str = "",
) -> None:
    width = 900
    height = 520
    margin_left = 90
    margin_right = 50
    margin_top = 80
    margin_bottom = 100

    values: list[tuple[str, float]] = []

    for row in rows:
        profile = row["profile"]
        value = safe_float(row.get(metric_key))

        if value is not None:
            values.append((profile, value))

    lines = svg_header(width, height)
    lines.append(f'<text x="{margin_left}" y="38" class="title">{html.escape(title)}</text>')
    lines.append(f'<text x="{margin_left}" y="58" class="subtitle">{html.escape(y_label)}</text>')

    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom
    x0 = margin_left
    y0 = height - margin_bottom

    lines.append(f'<line x1="{x0}" y1="{margin_top}" x2="{x0}" y2="{y0}" class="axis"/>')
    lines.append(f'<line x1="{x0}" y1="{y0}" x2="{width - margin_right}" y2="{y0}" class="axis"/>')

    if not values:
        lines.append(f'<text x="{margin_left}" y="{margin_top + 40}" class="label">No data</text>')
        lines.append("</svg>")
        write_svg(output_path, lines)
        return

    max_value = max(value for _, value in values)
    if max_value <= 0:
        max_value = 1.0

    y_max = max_value * 1.15

    ticks = 5
    for i in range(ticks + 1):
        tick_value = y_max * i / ticks
        y = y0 - (tick_value / y_max) * chart_height

        lines.append(f'<line x1="{x0}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" class="grid"/>')
        lines.append(
            f'<text x="{x0 - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">'
            f'{format_value(tick_value, unit)}</text>'
        )

    bar_gap = 40
    bar_width = (chart_width - bar_gap * (len(values) + 1)) / max(len(values), 1)
    bar_width = max(70, min(bar_width, 150))

    total_bars_width = len(values) * bar_width + (len(values) - 1) * bar_gap
    start_x = x0 + (chart_width - total_bars_width) / 2

    for index, (profile, value) in enumerate(values):
        x = start_x + index * (bar_width + bar_gap)
        bar_height = (value / y_max) * chart_height
        y = y0 - bar_height

        label = PROFILE_LABELS.get(profile, profile)

        lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{bar_height:.2f}" class="bar"/>')
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{y - 8:.2f}" text-anchor="middle" class="value">'
            f'{format_value(value, unit)}</text>'
        )
        lines.append(
            f'<text x="{x + bar_width / 2:.2f}" y="{y0 + 24:.2f}" text-anchor="middle" class="label">'
            f'{html.escape(label)}</text>'
        )

    lines.append("</svg>")
    write_svg(output_path, lines)


def handshake_range_chart(rows: list[dict[str, str]], output_path: Path) -> None:
    width = 900
    height = 520
    margin_left = 90
    margin_right = 50
    margin_top = 90
    margin_bottom = 100

    values: list[dict[str, Any]] = []

    for row in rows:
        minimum = safe_float(row.get("min_handshake_ms"))
        maximum = safe_float(row.get("max_handshake_ms"))
        median = safe_float(row.get("median_handshake_ms"))
        average = safe_float(row.get("avg_handshake_ms"))

        if minimum is None or maximum is None:
            continue

        values.append({
            "profile": row["profile"],
            "min": minimum,
            "max": maximum,
            "median": median,
            "avg": average,
        })

    lines = svg_header(width, height)
    lines.append(f'<text x="{margin_left}" y="38" class="title">TLS handshake time range</text>')
    lines.append(f'<text x="{margin_left}" y="58" class="subtitle">Min–max interval with median and average markers, ms</text>')

    chart_width = width - margin_left - margin_right
    chart_height = height - margin_top - margin_bottom
    x0 = margin_left
    y0 = height - margin_bottom

    lines.append(f'<line x1="{x0}" y1="{margin_top}" x2="{x0}" y2="{y0}" class="axis"/>')
    lines.append(f'<line x1="{x0}" y1="{y0}" x2="{width - margin_right}" y2="{y0}" class="axis"/>')

    if not values:
        lines.append(f'<text x="{margin_left}" y="{margin_top + 40}" class="label">No data</text>')
        lines.append("</svg>")
        write_svg(output_path, lines)
        return

    max_value = max(item["max"] for item in values)
    y_max = max(max_value * 1.15, 1.0)

    ticks = 5
    for i in range(ticks + 1):
        tick_value = y_max * i / ticks
        y = y0 - (tick_value / y_max) * chart_height

        lines.append(f'<line x1="{x0}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" class="grid"/>')
        lines.append(
            f'<text x="{x0 - 10}" y="{y + 4:.2f}" text-anchor="end" class="tick">'
            f'{format_value(tick_value, " ms")}</text>'
        )

    group_gap = chart_width / (len(values) + 1)

    for index, item in enumerate(values):
        x = x0 + group_gap * (index + 1)

        y_min = y0 - (item["min"] / y_max) * chart_height
        y_max_point = y0 - (item["max"] / y_max) * chart_height

        lines.append(f'<line x1="{x:.2f}" y1="{y_max_point:.2f}" x2="{x:.2f}" y2="{y_min:.2f}" class="range"/>')
        lines.append(f'<line x1="{x - 14:.2f}" y1="{y_min:.2f}" x2="{x + 14:.2f}" y2="{y_min:.2f}" class="range"/>')
        lines.append(f'<line x1="{x - 14:.2f}" y1="{y_max_point:.2f}" x2="{x + 14:.2f}" y2="{y_max_point:.2f}" class="range"/>')

        if item["median"] is not None:
            y_median = y0 - (item["median"] / y_max) * chart_height
            lines.append(f'<circle cx="{x:.2f}" cy="{y_median:.2f}" r="6" class="dot"/>')

        if item["avg"] is not None:
            y_avg = y0 - (item["avg"] / y_max) * chart_height
            lines.append(f'<rect x="{x - 5:.2f}" y="{y_avg - 5:.2f}" width="10" height="10" class="dot-alt"/>')

        label = PROFILE_LABELS.get(item["profile"], item["profile"])

        lines.append(
            f'<text x="{x:.2f}" y="{y0 + 24:.2f}" text-anchor="middle" class="label">'
            f'{html.escape(label)}</text>'
        )

    legend_x = width - margin_right - 190
    legend_y = margin_top - 34

    lines.append(f'<circle cx="{legend_x}" cy="{legend_y}" r="5" class="dot"/>')
    lines.append(f'<text x="{legend_x + 12}" y="{legend_y + 4}" class="tick">median</text>')
    lines.append(f'<rect x="{legend_x + 80}" y="{legend_y - 5}" width="10" height="10" class="dot-alt"/>')
    lines.append(f'<text x="{legend_x + 96}" y="{legend_y + 4}" class="tick">average</text>')

    lines.append("</svg>")
    write_svg(output_path, lines)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    summary_csv = root / "artifacts" / "reports" / "summary-all.csv"
    charts_dir = root / "artifacts" / "reports" / "charts"

    rows = read_summary_rows(summary_csv)

    chart_specs = [
        (
            "avg_handshake_ms",
            charts_dir / "avg-handshake-ms.svg",
            "Average TLS handshake time",
            "Average handshake time by profile",
            " ms",
        ),
        (
            "total_pipeline_duration_ms",
            charts_dir / "total-pipeline-duration-ms.svg",
            "Total pipeline duration",
            "Total CI/CD profile run duration",
            " ms",
        ),
        (
            "test_duration_ms",
            charts_dir / "test-stage-duration-ms.svg",
            "Integration test stage duration",
            "TLS handshake test stage duration",
            " ms",
        ),
        (
            "server_cpu_max_percent",
            charts_dir / "cpu-max-percent.svg",
            "Maximum server CPU usage",
            "Maximum sampled CPU usage during handshake tests",
            "%",
        ),
        (
            "server_memory_max_mib",
            charts_dir / "memory-max-mib.svg",
            "Maximum server memory usage",
            "Maximum sampled memory usage during handshake tests",
            " MiB",
        ),
        (
            "cert_chain_size_bytes",
            charts_dir / "cert-chain-size-bytes.svg",
            "Certificate chain size",
            "CA certificate + server certificate size",
            " B",
        ),
    ]

    for metric_key, output_path, title, y_label, unit in chart_specs:
        bar_chart(rows, metric_key, output_path, title, y_label, unit)

    handshake_range_chart(rows, charts_dir / "handshake-range-ms.svg")

    print("[charts] Charts generated:")
    for path in sorted(charts_dir.glob("*.svg")):
        print(f"[charts] - {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())