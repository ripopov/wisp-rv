#!/usr/bin/env python3
import argparse
import json
import re
from collections import Counter
from pathlib import Path


def parse_status(value: str) -> str:
    if not value:
        return "unknown"
    value = value.strip().lower()
    if value in {"success", "passed", "pass"}:
        return "success"
    if value in {"failure", "failed", "fail"}:
        return "failure"
    if value in {"skipped", "cancelled", "unknown"}:
        return value
    return value


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_clock_period_ns(sdc_path: Path):
    text = read_text(sdc_path)
    m = re.search(r"create_clock\s+.*?-period\s+([0-9]+(?:\.[0-9]+)?)", text)
    if not m:
        return None
    return float(m.group(1))


def parse_wns_max_ns(wns_path: Path):
    text = read_text(wns_path)
    m = re.search(r"worst\s+slack\s+max\s+(-?[0-9]+(?:\.[0-9]+)?)", text)
    if not m:
        return None
    return float(m.group(1))


def parse_tns_max_ns(tns_path: Path):
    text = read_text(tns_path)
    m = re.search(r"tns\s+max\s+(-?[0-9]+(?:\.[0-9]+)?)", text)
    if not m:
        return None
    return float(m.group(1))


def count_std_cells(netlist_path: Path):
    counts = Counter()
    text = read_text(netlist_path)

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("/*"):
            continue

        m = re.match(
            r"([A-Za-z_][A-Za-z0-9_$]*)\s+([A-Za-z_][A-Za-z0-9_$]*)\s*\(", line
        )
        if not m:
            continue

        cell_type = m.group(1)
        if re.search(r"_X[0-9]+$", cell_type):
            counts[cell_type] += 1

    return sum(counts.values()), counts


def parse_critical_path_excerpt(checks_max_path: Path, max_lines: int = 40):
    text = read_text(checks_max_path)
    if not text:
        return "Unavailable (checks_max.rpt missing)."

    lines = text.splitlines()
    excerpt = []
    in_path = False

    for line in lines:
        if not in_path and line.strip().startswith("Startpoint:"):
            in_path = True

        if not in_path:
            continue

        excerpt.append(line)
        if "slack (" in line:
            break

        if len(excerpt) >= max_lines:
            break

    if not excerpt:
        return "Unavailable (could not parse first max path)."

    return "\n".join(excerpt)


def status_emoji(status: str) -> str:
    if status == "success":
        return "PASS"
    if status == "failure":
        return "FAIL"
    if status == "skipped":
        return "SKIP"
    if status == "cancelled":
        return "CANCEL"
    return "UNKNOWN"


def fmt_num(value, digits=3):
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def main():
    parser = argparse.ArgumentParser(
        description="Generate CI markdown report for sim/synth/STA flow."
    )
    parser.add_argument("--setup-status", default="unknown")
    parser.add_argument("--openram-status", default="unknown")
    parser.add_argument("--sim-status", default="unknown")
    parser.add_argument("--synth-status", default="unknown")
    parser.add_argument("--sta-status", default="unknown")
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--output-json", required=False)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    setup_status = parse_status(args.setup_status)
    openram_status = parse_status(args.openram_status)
    sim_status = parse_status(args.sim_status)
    synth_status = parse_status(args.synth_status)
    sta_status = parse_status(args.sta_status)

    sdc_path = root / "constraints" / "set_assoc_cache_2way.sdc"
    netlist_path = root / "build" / "synth" / "set_assoc_cache_2way_synth.v"
    wns_path = root / "reports" / "sta" / "wns_max.rpt"
    tns_path = root / "reports" / "sta" / "tns.rpt"
    checks_max_path = root / "reports" / "sta" / "checks_max.rpt"

    clock_period_ns = parse_clock_period_ns(sdc_path)
    wns_max_ns = parse_wns_max_ns(wns_path)
    tns_max_ns = parse_tns_max_ns(tns_path)

    fmax_mhz = None
    max_freq_period_ns = None
    if clock_period_ns is not None and wns_max_ns is not None:
        max_freq_period_ns = clock_period_ns - wns_max_ns
        if max_freq_period_ns > 0:
            fmax_mhz = 1000.0 / max_freq_period_ns

    gate_count, gate_breakdown = count_std_cells(netlist_path)
    top_cells = gate_breakdown.most_common(10)
    critical_excerpt = parse_critical_path_excerpt(checks_max_path)

    stages = [
        ("Setup", setup_status),
        ("OpenRAM", openram_status),
        ("Simulation", sim_status),
        ("Synthesis", synth_status),
        ("Pre-PnR STA", sta_status),
    ]

    lines = []
    lines.append("# CI Report")
    lines.append("")
    lines.append("## Stage Status")
    lines.append("")
    lines.append("| Stage | Status |")
    lines.append("|---|---|")
    for stage_name, stage_status in stages:
        lines.append(
            f"| {stage_name} | {status_emoji(stage_status)} (`{stage_status}`) |"
        )
    lines.append("")
    lines.append("## Synthesis Summary")
    lines.append("")
    lines.append(f"- Standard-cell gate count: `{gate_count if gate_count else 'N/A'}`")
    if top_cells:
        lines.append("- Top cell usage:")
        for cell, count in top_cells:
            lines.append(f"  - `{cell}`: `{count}`")
    else:
        lines.append("- Top cell usage: `N/A`")
    lines.append("")
    lines.append("## STA Summary")
    lines.append("")
    lines.append(f"- Constraint clock period: `{fmt_num(clock_period_ns)} ns`")
    lines.append(f"- Setup WNS: `{fmt_num(wns_max_ns)} ns`")
    lines.append(f"- Setup TNS: `{fmt_num(tns_max_ns)} ns`")
    lines.append(f"- Implied max frequency: `{fmt_num(fmax_mhz)} MHz`")
    lines.append(f"- Implied minimum period: `{fmt_num(max_freq_period_ns)} ns`")
    lines.append("")
    lines.append("## Critical Path (Max)")
    lines.append("")
    lines.append("```text")
    lines.append(critical_excerpt)
    lines.append("```")
    lines.append("")
    lines.append("## Raw Reports")
    lines.append("")
    lines.append("- `reports/sta/checks_max.rpt`")
    lines.append("- `reports/sta/checks_min.rpt`")
    lines.append("- `reports/sta/wns_max.rpt`")
    lines.append("- `reports/sta/wns_min.rpt`")
    lines.append("- `reports/sta/tns.rpt`")

    markdown = "\n".join(lines) + "\n"
    output_md.write_text(markdown, encoding="utf-8")

    payload = {
        "stages": {name.lower().replace(" ", "_"): status for name, status in stages},
        "synthesis": {
            "standard_cell_gate_count": gate_count,
            "top_cells": [{"cell": cell, "count": count} for cell, count in top_cells],
        },
        "sta": {
            "clock_period_ns": clock_period_ns,
            "wns_max_ns": wns_max_ns,
            "tns_max_ns": tns_max_ns,
            "implied_min_period_ns": max_freq_period_ns,
            "implied_max_frequency_mhz": fmax_mhz,
        },
        "paths": {
            "critical_path_excerpt": critical_excerpt,
        },
    }

    if args.output_json:
        output_json = Path(args.output_json)
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
