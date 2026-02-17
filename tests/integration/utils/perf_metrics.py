from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class PerfSample:
    name: str
    category: str
    cycles: int
    retired: int
    compile_seconds: float
    sim_seconds: float

    @property
    def cpi(self) -> float:
        if self.retired <= 0:
            return float("inf")
        return self.cycles / float(self.retired)


@dataclass(frozen=True)
class PerfThresholds:
    min_retired: int = 1
    max_cycles: int | None = None
    max_cpi: float | None = None
    max_compile_seconds: float | None = None
    max_sim_seconds: float | None = None


def evaluate_thresholds(sample: PerfSample, thresholds: PerfThresholds) -> list[str]:
    failures: list[str] = []

    if sample.retired < thresholds.min_retired:
        failures.append(
            f"retired too low ({sample.retired} < {thresholds.min_retired})"
        )
    if thresholds.max_cycles is not None and sample.cycles > thresholds.max_cycles:
        failures.append(f"cycles too high ({sample.cycles} > {thresholds.max_cycles})")
    if thresholds.max_cpi is not None and sample.cpi > thresholds.max_cpi:
        failures.append(f"CPI too high ({sample.cpi:.3f} > {thresholds.max_cpi:.3f})")
    if (
        thresholds.max_compile_seconds is not None
        and sample.compile_seconds > thresholds.max_compile_seconds
    ):
        failures.append(
            "compile time too high "
            f"({sample.compile_seconds:.3f}s > {thresholds.max_compile_seconds:.3f}s)"
        )
    if (
        thresholds.max_sim_seconds is not None
        and sample.sim_seconds > thresholds.max_sim_seconds
    ):
        failures.append(
            f"sim time too high ({sample.sim_seconds:.3f}s > {thresholds.max_sim_seconds:.3f}s)"
        )

    return failures


def format_perf_table(samples: list[PerfSample]) -> str:
    header = (
        f"{'benchmark':<18} {'category':<10} {'cycles':>8} {'retired':>8} "
        f"{'cpi':>8} {'compile_s':>10} {'sim_s':>8}"
    )
    rows = [header, "-" * len(header)]
    for sample in samples:
        rows.append(
            f"{sample.name:<18} {sample.category:<10} {sample.cycles:>8d} "
            f"{sample.retired:>8d} {sample.cpi:>8.3f} "
            f"{sample.compile_seconds:>10.3f} {sample.sim_seconds:>8.3f}"
        )
    return "\n".join(rows)


def summarize_by_category(samples: list[PerfSample]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[PerfSample]] = {}
    for sample in samples:
        grouped.setdefault(sample.category, []).append(sample)

    summary: dict[str, dict[str, float]] = {}
    for category, group in grouped.items():
        summary[category] = {
            "count": float(len(group)),
            "avg_cycles": mean(s.cycles for s in group),
            "avg_cpi": mean(s.cpi for s in group),
            "avg_compile_seconds": mean(s.compile_seconds for s in group),
            "avg_sim_seconds": mean(s.sim_seconds for s in group),
        }
    return summary


def format_category_summary(samples: list[PerfSample]) -> str:
    summary = summarize_by_category(samples)
    header = (
        f"{'category':<10} {'count':>5} {'avg_cycles':>12} {'avg_cpi':>10} "
        f"{'avg_compile_s':>14} {'avg_sim_s':>10}"
    )
    rows = [header, "-" * len(header)]
    for category in sorted(summary):
        row = summary[category]
        rows.append(
            f"{category:<10} {int(row['count']):>5d} {row['avg_cycles']:>12.1f} "
            f"{row['avg_cpi']:>10.3f} {row['avg_compile_seconds']:>14.3f} "
            f"{row['avg_sim_seconds']:>10.3f}"
        )
    return "\n".join(rows)
