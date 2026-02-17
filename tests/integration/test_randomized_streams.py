from __future__ import annotations

import json
import os
import random
import sys
import tempfile
from pathlib import Path

import cocotb
from cocotb.clock import Clock

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from utils.build_rv64_program import DEFAULT_MABI, DEFAULT_MARCH, build_rv64_program
from utils.elf_loader import elf_image_to_byte_map, load_elf_image
from utils.reference_model import Rv64ReferenceModel
from utils.sim_harness import (
    init_tb_ports,
    reset_and_load_elf,
    run_until_termination,
    tb_read_u64,
)

TOHOST_ADDR = 0x7C0
SIGNATURE_BASE = 0x700
RANDOM_REGS = (1, 2, 3, 4, 5, 6, 7, 8)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw, 0)


def _gen_random_alu_program(seed: int, op_count: int) -> str:
    rng = random.Random(seed)
    lines = [".section .text", ".globl _start", "", "_start:"]

    for reg in RANDOM_REGS:
        imm = rng.randint(-1024, 1023)
        lines.append(f"    addi x{reg}, x0, {imm}")

    op_kinds = (
        "addi",
        "xori",
        "ori",
        "andi",
        "slli",
        "srli",
        "srai",
        "add",
        "sub",
        "xor",
        "or",
        "and",
        "sll",
        "srl",
        "sra",
    )

    for _ in range(op_count):
        kind = rng.choice(op_kinds)
        rd = rng.choice(RANDOM_REGS)
        rs1 = rng.choice(RANDOM_REGS)

        if kind in ("addi", "xori", "ori", "andi"):
            imm = rng.randint(-2048, 2047)
            lines.append(f"    {kind} x{rd}, x{rs1}, {imm}")
        elif kind in ("slli", "srli", "srai"):
            shamt = rng.randint(0, 63)
            lines.append(f"    {kind} x{rd}, x{rs1}, {shamt}")
        else:
            rs2 = rng.choice(RANDOM_REGS)
            lines.append(f"    {kind} x{rd}, x{rs1}, x{rs2}")

    for idx, reg in enumerate(RANDOM_REGS):
        addr = SIGNATURE_BASE + idx * 8
        lines.append(f"    sd x{reg}, 0x{addr:x}(x0)")

    lines.extend(
        [
            "    addi x31, x0, 1",
            f"    sd x31, 0x{TOHOST_ADDR:x}(x0)",
            "",
            "done:",
            "    jal x0, done",
        ]
    )

    return "\n".join(lines) + "\n"


def _write_failure_artifacts(
    *,
    seed: int,
    asm_text: str,
    disasm_text: str,
    expected_regs: dict[str, int],
    observed_regs: dict[str, int],
    details: dict[str, object],
) -> Path:
    out_dir = Path(tempfile.mkdtemp(prefix=f"wisp-rv64-randfail-{seed}-"))
    (out_dir / "program.S").write_text(asm_text)
    (out_dir / "program.dump").write_text(disasm_text)
    (out_dir / "expected_regs.json").write_text(
        json.dumps(expected_regs, indent=2, sort_keys=True)
    )
    (out_dir / "observed_regs.json").write_text(
        json.dumps(observed_regs, indent=2, sort_keys=True)
    )
    (out_dir / "details.json").write_text(json.dumps(details, indent=2, sort_keys=True))
    return out_dir


@cocotb.test()
async def test_randomized_streams_against_reference_model(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    base_seed = _env_int("WISP_RAND_SEED", 0x5A17_0001)
    case_count = _env_int("WISP_RAND_CASES", 3)
    op_count = _env_int("WISP_RAND_OPS", 160)

    dut._log.info(
        "Random stream config: base_seed=%d case_count=%d op_count=%d",
        base_seed,
        case_count,
        op_count,
    )

    total_cycles = 0

    for case_idx in range(case_count):
        seed = base_seed + case_idx
        asm_text = _gen_random_alu_program(seed, op_count)

        with tempfile.TemporaryDirectory(prefix=f"wisp-rv64-rand-{seed}-") as tmpdir:
            tmp = Path(tmpdir)
            src = tmp / f"rand_{seed}.S"
            src.write_text(asm_text)

            artifacts = build_rv64_program(
                source=src,
                linker_script=THIS_DIR / "linker" / "rv64.ld",
                output_dir=tmp,
                march=DEFAULT_MARCH,
                mabi=DEFAULT_MABI,
            )

            image = load_elf_image(artifacts.elf_path)
            ref = Rv64ReferenceModel()
            expected = ref.run(
                initial_pc=image.entry_point,
                memory=elf_image_to_byte_map(image),
                max_steps=op_count + 512,
                tohost_addr=TOHOST_ADDR,
                stop_on_tohost=True,
            )

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
                max_cycles=30_000,
                tohost_addr=TOHOST_ADDR,
                tohost_drain_cycles=8,
                halt_repeat_cycles=48,
            )
            total_cycles += result.cycles

            try:
                assert result.tohost == 1, (
                    f"seed={seed}: tohost mismatch ({result.tohost})"
                    f" reason={result.reason} recent_if_pcs={[hex(pc) for pc in result.recent_if_pcs]}"
                )

                for reg in RANDOM_REGS:
                    got = result.wb_regs[reg]
                    exp = expected.regs[reg]
                    assert got == exp, (
                        f"seed={seed}: register mismatch x{reg}: "
                        f"expected 0x{exp:016x}, got 0x{got:016x}"
                    )

                for idx, reg in enumerate(RANDOM_REGS):
                    addr = SIGNATURE_BASE + idx * 8
                    got = await tb_read_u64(dut, addr)
                    exp = expected.regs[reg]
                    assert got == exp, (
                        f"seed={seed}: signature mismatch at 0x{addr:03x}: "
                        f"expected 0x{exp:016x}, got 0x{got:016x}"
                    )

                assert result.cycles <= 10_000, (
                    f"seed={seed}: cycle budget exceeded ({result.cycles} > 10000)"
                )
            except AssertionError as exc:
                exp_regs = {f"x{reg}": expected.regs[reg] for reg in RANDOM_REGS}
                got_regs = {f"x{reg}": result.wb_regs[reg] for reg in RANDOM_REGS}
                details = {
                    "seed": seed,
                    "case_index": case_idx,
                    "reason": result.reason,
                    "cycles": result.cycles,
                    "tohost": result.tohost,
                    "recent_if_pcs": [hex(pc) for pc in result.recent_if_pcs],
                    "retired_count": len(result.retire_pcs),
                }
                artifact_dir = _write_failure_artifacts(
                    seed=seed,
                    asm_text=asm_text,
                    disasm_text=artifacts.dump_path.read_text(),
                    expected_regs=exp_regs,
                    observed_regs=got_regs,
                    details=details,
                )
                raise AssertionError(
                    f"Random stream mismatch for seed={seed}; artifacts at {artifact_dir}"
                ) from exc

            dut._log.info(
                "Random stream seed=%d passed in %d cycles",
                seed,
                result.cycles,
            )

    assert total_cycles <= 24_000, (
        f"Random suite cycle budget exceeded ({total_cycles})"
    )
