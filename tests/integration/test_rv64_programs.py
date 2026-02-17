from __future__ import annotations

import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cocotb
from cocotb.clock import Clock

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from utils.build_rv64_program import DEFAULT_MABI, DEFAULT_MARCH, build_rv64_program
from utils.elf_loader import load_elf_image
from utils.sim_harness import (
    init_tb_ports,
    reset_and_load_elf,
    run_until_termination,
    tb_read_u64,
)

TOHOST_ADDR = 0x200
DISASM_PC_RE = re.compile(r"^\s*([0-9a-f]+):\s", re.MULTILINE)


@dataclass(frozen=True)
class ProgramCase:
    name: str
    source: Path
    expected_dmem: dict[int, int]
    cycle_budget: int


def _parse_disasm_pcs(dump_text: str) -> set[int]:
    pcs = {int(match.group(1), 16) for match in DISASM_PC_RE.finditer(dump_text)}
    if not pcs:
        raise AssertionError("Disassembly did not contain any instruction PCs")
    return pcs


PROGRAM_CASES = (
    ProgramCase(
        name="stage12_core_suite",
        source=THIS_DIR / "programs" / "stage12_core_suite.S",
        expected_dmem={
            0x300: 30,
            0x310: 14,
            0x318: 1,
            0x320: 77,
            0x328: 42,
            0x330: 0,
            0x338: 0,
            0x340: 0x55,
            0x348: 0x0000_0000_0055_0022,
            0x350: 0x55,
            0x358: 0x55,
        },
        cycle_budget=2_500,
    ),
    ProgramCase(
        name="stage9_smoke",
        source=THIS_DIR / "programs" / "stage9_smoke.S",
        expected_dmem={
            0x100: 15,
            0x130: 2,
            0x148: 11,
            0x198: 42,
            0x1C0: 14,
            0x230: 15,
        },
        cycle_budget=6_000,
    ),
)


@cocotb.test()
async def test_curated_rv64_program_suite(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    total_cycles = 0

    for case in PROGRAM_CASES:
        with tempfile.TemporaryDirectory(prefix=f"wisp-rv64-{case.name}-") as tmpdir:
            artifacts = build_rv64_program(
                source=case.source,
                linker_script=THIS_DIR / "linker" / "rv64.ld",
                output_dir=Path(tmpdir),
                march=DEFAULT_MARCH,
                mabi=DEFAULT_MABI,
            )

            image = load_elf_image(artifacts.elf_path)
            disasm_pcs = _parse_disasm_pcs(artifacts.dump_path.read_text())

            await reset_and_load_elf(
                dut,
                image,
                reset_cycles=2,
                clear_words=1024,
                load_imem=True,
                load_dmem=True,
            )

            result = await run_until_termination(
                dut,
                max_cycles=20_000,
                tohost_addr=TOHOST_ADDR,
                tohost_drain_cycles=8,
                halt_repeat_cycles=48,
            )

            total_cycles += result.cycles

            assert result.tohost == 1, (
                f"{case.name}: tohost mismatch ({result.tohost})"
                f" reason={result.reason} recent_if_pcs={[hex(pc) for pc in result.recent_if_pcs]}"
            )

            for addr, expected in case.expected_dmem.items():
                got = await tb_read_u64(dut, addr)
                assert got == expected, (
                    f"{case.name}: memory mismatch at 0x{addr:03x}: "
                    f"expected 0x{expected:016x}, got 0x{got:016x}"
                )

            assert result.cycles <= case.cycle_budget, (
                f"{case.name}: cycle budget exceeded "
                f"({result.cycles} > {case.cycle_budget})"
            )

            assert result.retire_pcs, f"{case.name}: retire trace is empty"
            unexpected = [pc for pc in result.retire_pcs if pc not in disasm_pcs]
            assert not unexpected, (
                f"{case.name}: retire PCs not found in disassembly "
                f"(sample={[hex(pc) for pc in unexpected[:8]]})"
            )

            dut._log.info(
                "Program %s completed in %d cycles; retired=%d",
                case.name,
                result.cycles,
                len(result.retire_pcs),
            )

    assert total_cycles <= 9_000, (
        f"Curated suite cycle budget exceeded ({total_cycles})"
    )
