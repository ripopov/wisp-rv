from __future__ import annotations

import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import cocotb
from cocotb.clock import Clock

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from utils.build_rv64_program import DEFAULT_MABI, DEFAULT_MARCH, build_rv64_program
from utils.elf_loader import load_elf_image
from utils.perf_metrics import (
    PerfSample,
    PerfThresholds,
    evaluate_thresholds,
    format_category_summary,
    format_perf_table,
)
from utils.sim_harness import (
    init_tb_ports,
    reset_and_load_elf,
    run_until_termination,
    tb_read_u64,
)

MASK64 = (1 << 64) - 1
TOHOST_ADDR = 0x200


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    category: str
    source: Path
    expected_dmem: dict[int, int]
    thresholds: PerfThresholds
    extra_gcc_flags: tuple[str, ...] = ()


def _alu_chain_expected() -> dict[int, int]:
    x1, x2, x3 = 1, 2, 3
    for _ in range(200):
        x1 = (x1 + x2) & MASK64
        x2 = (x2 ^ x3) & MASK64
        x3 = (x3 + x1) & MASK64
    return {
        0x400: x1,
        0x408: x2,
        0x410: x3,
    }


def _dhrystone_smoke_expected() -> int:
    a, b, c = 1, 2, 3
    for i in range(300):
        a = (a + (((b << 1) & MASK64) ^ i)) & MASK64
        b = (b + (a >> 3) + c) & MASK64
        c = (c ^ ((a + b + i) & MASK64)) & MASK64
    return (a ^ b ^ c) & MASK64


def _coremark_smoke_expected() -> int:
    buf = [((i * 3) + 1) & MASK64 for i in range(32)]
    crc = 0
    for i in range(32):
        value = buf[i]
        value = (((value << 2) & MASK64) ^ (crc >> 1) ^ i) & MASK64
        crc = (crc + value) & MASK64
        buf[i] = value
    return crc


BENCHMARK_CASES = (
    BenchmarkCase(
        name="alu_chain",
        category="alu",
        source=THIS_DIR / "benchmarks" / "alu_chain.S",
        expected_dmem=_alu_chain_expected(),
        thresholds=PerfThresholds(
            min_retired=800,
            max_cycles=2500,
            max_cpi=3.0,
            max_compile_seconds=3.0,
            max_sim_seconds=2.0,
        ),
    ),
    BenchmarkCase(
        name="branch_maze",
        category="branch",
        source=THIS_DIR / "benchmarks" / "branch_maze.S",
        expected_dmem={0x418: 1600},
        thresholds=PerfThresholds(
            min_retired=2200,
            max_cycles=7000,
            max_cpi=3.5,
            max_compile_seconds=3.0,
            max_sim_seconds=2.0,
        ),
    ),
    BenchmarkCase(
        name="memcpy",
        category="memory",
        source=THIS_DIR / "benchmarks" / "memcpy.S",
        expected_dmem={0x420: 0x1F1},
        thresholds=PerfThresholds(
            min_retired=400,
            max_cycles=4000,
            max_cpi=4.5,
            max_compile_seconds=3.0,
            max_sim_seconds=2.0,
        ),
    ),
    BenchmarkCase(
        name="dhrystone_smoke",
        category="integer",
        source=THIS_DIR / "benchmarks" / "dhrystone_smoke.c",
        expected_dmem={0x428: _dhrystone_smoke_expected()},
        thresholds=PerfThresholds(
            min_retired=1700,
            max_cycles=7000,
            max_cpi=4.0,
            max_compile_seconds=3.0,
            max_sim_seconds=2.0,
        ),
        extra_gcc_flags=("-O2",),
    ),
    BenchmarkCase(
        name="coremark_smoke",
        category="mixed",
        source=THIS_DIR / "benchmarks" / "coremark_smoke.c",
        expected_dmem={0x430: _coremark_smoke_expected()},
        thresholds=PerfThresholds(
            min_retired=350,
            max_cycles=6000,
            max_cpi=4.5,
            max_compile_seconds=3.0,
            max_sim_seconds=2.0,
        ),
        extra_gcc_flags=("-O2",),
    ),
)


@cocotb.test()
async def test_perf_smoke_regression_gates(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    samples: list[PerfSample] = []

    for case in BENCHMARK_CASES:
        with tempfile.TemporaryDirectory(
            prefix=f"wisp-rv64-perf-{case.name}-"
        ) as tmpdir:
            build_start = time.perf_counter()
            artifacts = build_rv64_program(
                source=case.source,
                linker_script=THIS_DIR / "linker" / "rv64.ld",
                output_dir=Path(tmpdir),
                march=DEFAULT_MARCH,
                mabi=DEFAULT_MABI,
                extra_gcc_flags=case.extra_gcc_flags,
            )
            compile_seconds = time.perf_counter() - build_start

            image = load_elf_image(artifacts.elf_path)

            await reset_and_load_elf(
                dut,
                image,
                reset_cycles=2,
                clear_words=1024,
                load_imem=True,
                load_dmem=True,
            )

            sim_start = time.perf_counter()
            run_result = await run_until_termination(
                dut,
                max_cycles=25_000,
                tohost_addr=TOHOST_ADDR,
                tohost_drain_cycles=8,
                halt_repeat_cycles=64,
            )
            sim_seconds = time.perf_counter() - sim_start

            assert run_result.tohost == 1, (
                f"{case.name}: completion mismatch (tohost={run_result.tohost}) "
                f"reason={run_result.reason} "
                f"recent_if_pcs={[hex(pc) for pc in run_result.recent_if_pcs]}"
            )

            for addr, expected in case.expected_dmem.items():
                got = await tb_read_u64(dut, addr)
                assert got == expected, (
                    f"{case.name}: memory mismatch at 0x{addr:03x}: "
                    f"expected 0x{expected:016x}, got 0x{got:016x}"
                )

            sample = PerfSample(
                name=case.name,
                category=case.category,
                cycles=run_result.cycles,
                retired=len(run_result.retire_pcs),
                compile_seconds=compile_seconds,
                sim_seconds=sim_seconds,
            )
            failures = evaluate_thresholds(sample, case.thresholds)
            assert not failures, f"{case.name}: threshold failure(s): {failures}"
            samples.append(sample)

    table = format_perf_table(samples)
    category_summary = format_category_summary(samples)
    dut._log.info("Performance summary:\n%s", table)
    dut._log.info("Category summary:\n%s", category_summary)

    total_cycles = sum(sample.cycles for sample in samples)
    total_compile_seconds = sum(sample.compile_seconds for sample in samples)
    total_sim_seconds = sum(sample.sim_seconds for sample in samples)

    assert total_cycles <= 20_000, (
        f"Total benchmark cycles exceed budget ({total_cycles} > 20000)"
    )
    assert total_compile_seconds <= 15.0, (
        f"Total compile time exceeds budget ({total_compile_seconds:.3f}s > 15.000s)"
    )
    assert total_sim_seconds <= 10.0, (
        f"Total simulation wall time exceeds budget ({total_sim_seconds:.3f}s > 10.000s)"
    )
