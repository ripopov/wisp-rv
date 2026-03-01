#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return str(value)


def sort_key(item: dict[str, Any]) -> tuple[int, float, str]:
    status = item.get("status", "failure")
    fmax = item.get("fmax_mhz")
    if status == "success" and isinstance(fmax, (int, float)):
        return (0, -float(fmax), item.get("design_name", ""))
    return (1, 0.0, item.get("design_name", ""))


def load_results(results_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for json_path in sorted(results_dir.glob("*/result.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows.append(
                {
                    "design_name": json_path.parent.name,
                    "category": "unknown",
                    "status": "failure",
                    "error_message": "invalid_result_json",
                    "report_dir": str(json_path.parent),
                }
            )
            continue
        rows.append(payload)
    return rows


def build_markdown(rows: list[dict[str, Any]]) -> str:
    rows_sorted = sorted(rows, key=sort_key)
    success_rows = [row for row in rows_sorted if row.get("status") == "success"]
    failure_rows = [row for row in rows_sorted if row.get("status") != "success"]

    lines: list[str] = []
    lines.append("# Nangate45 / OpenRAM FreePDK45 Exploration")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total designs: `{len(rows_sorted)}`")
    lines.append(f"- Successful designs: `{len(success_rows)}`")
    lines.append(f"- Failed designs: `{len(failure_rows)}`")
    lines.append("")
    lines.append("## Frequency Ranking")
    lines.append("")
    lines.append("| Rank | Design | Category | Fmax (MHz) | Period (ns) | WNS (ns) | TNS (ns) | Status |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|")

    rank = 1
    for row in rows_sorted:
        is_success = row.get("status") == "success"
        shown_rank = str(rank) if is_success else "-"
        if is_success:
            rank += 1
        lines.append(
            "| {rank} | {design} | {category} | {fmax} | {period} | {wns} | {tns} | {status} |".format(
                rank=shown_rank,
                design=row.get("design_name", "unknown"),
                category=row.get("category", "unknown"),
                fmax=fmt(row.get("fmax_mhz")),
                period=fmt(row.get("clock_period_ns_at_wns_zero")),
                wns=fmt(row.get("wns_ns")),
                tns=fmt(row.get("tns_ns")),
                status=row.get("status", "unknown"),
            )
        )

    if failure_rows:
        lines.append("")
        lines.append("## Failures")
        lines.append("")
        for row in failure_rows:
            lines.append(
                "- `{name}`: `{error}`".format(
                    name=row.get("design_name", "unknown"),
                    error=row.get("error_message", "unspecified_error"),
                )
            )

    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("- `reports/studies/nangate45_openram_freepdk45/per_design/`")
    lines.append("- `reports/studies/nangate45_openram_freepdk45/summary.json`")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate markdown/json summary for nangate45 exploration results."
    )
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=True)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    output_md = Path(args.output_md)
    output_json = Path(args.output_json)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.parent.mkdir(parents=True, exist_ok=True)

    rows = load_results(results_dir)
    rows_sorted = sorted(rows, key=sort_key)
    success_rows = [row for row in rows_sorted if row.get("status") == "success"]
    failure_rows = [row for row in rows_sorted if row.get("status") != "success"]

    summary = {
        "study": "nangate45_openram_freepdk45",
        "totals": {
            "designs": len(rows_sorted),
            "successes": len(success_rows),
            "failures": len(failure_rows),
        },
        "results": rows_sorted,
    }

    output_md.write_text(build_markdown(rows_sorted), encoding="utf-8")
    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
