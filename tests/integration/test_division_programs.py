from __future__ import annotations

import sys
import tempfile
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

MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1
TOHOST_ADDR = 0x7000
RESULT_BASE = 0x7040
RESULT_BASE_DIRECTED = 0x7080
MIN_S64 = -(1 << 63)
MIN_S32 = -(1 << 31)

EDGE_S64 = (
    0,
    1,
    -1,
    2,
    -2,
    7,
    -7,
    0x7FFF_FFFF_FFFF_FFFF,
    MIN_S64,
    0x4000_0000_0000_0000,
    -0x4000_0000_0000_0000,
    0x0123_4567_89AB_CDEF,
)

EDGE_U64 = (
    0x0000_0000_0000_0000,
    0x0000_0000_0000_0001,
    0x0000_0000_0000_0002,
    0x0000_0000_0000_0003,
    0x0000_0000_0000_0007,
    0x0000_0000_0000_0008,
    0xFFFF_FFFF_FFFF_FFFF,
    0x8000_0000_0000_0000,
    0x7FFF_FFFF_FFFF_FFFF,
    0x0000_0001_0000_0000,
    0x0000_0000_FFFF_FFFF,
    0x1234_5678_9ABC_DEF0,
)

EDGE_S32 = (
    0,
    1,
    -1,
    2,
    -2,
    7,
    -7,
    0x7FFF_FFFF,
    MIN_S32,
    0x4000_0000,
    -0x4000_0000,
    0x1234_5678,
)


def u64(value: int) -> int:
    return value & MASK64


def u32(value: int) -> int:
    return value & MASK32


def s32(value: int) -> int:
    value &= MASK32
    if value & (1 << 31):
        return value - (1 << 32)
    return value


def trunc_div(a: int, b: int) -> int:
    sign = -1 if ((a < 0) ^ (b < 0)) else 1
    return sign * (abs(a) // abs(b))


def trunc_rem(a: int, b: int) -> int:
    return a - trunc_div(a, b) * b


def mix(acc: int, value: int) -> int:
    return u64(
        acc ^ u64(value + 0x9E37_79B9_7F4A_7C15 + ((acc << 6) & MASK64) + (acc >> 2))
    )


def expected_hashes() -> tuple[int, ...]:
    h_div = 0x1111_1111_1111_1111
    h_divu = 0x2222_2222_2222_2222
    h_rem = 0x3333_3333_3333_3333
    h_remu = 0x4444_4444_4444_4444
    h_divw = 0x5555_5555_5555_5555
    h_divuw = 0x6666_6666_6666_6666
    h_remw = 0x7777_7777_7777_7777
    h_remuw = 0x8888_8888_8888_8888
    iters = 0

    for a in range(-16, 16):
        for b in range(-16, 16):
            if b == 0:
                q = -1
                r = a
            elif a == MIN_S64 and b == -1:
                q = MIN_S64
                r = 0
            else:
                q = trunc_div(a, b)
                r = trunc_rem(a, b)

            ua = u64(a)
            ub = u64(b)
            qu = MASK64 if ub == 0 else (ua // ub)
            ru = ua if ub == 0 else (ua % ub)

            aw = s32(a)
            bw = s32(b)
            if bw == 0:
                qw = -1
                rw = aw
            elif aw == MIN_S32 and bw == -1:
                qw = MIN_S32
                rw = 0
            else:
                qw = trunc_div(aw, bw)
                rw = trunc_rem(aw, bw)

            auw = u32(aw)
            buw = u32(bw)
            quw_bits = MASK32 if buw == 0 else (auw // buw)
            ruw_bits = auw if buw == 0 else (auw % buw)
            quw = s32(quw_bits)
            ruw = s32(ruw_bits)

            h_div = mix(h_div, u64(q))
            h_divu = mix(h_divu, qu)
            h_rem = mix(h_rem, u64(r))
            h_remu = mix(h_remu, ru)
            h_divw = mix(h_divw, u64(qw))
            h_divuw = mix(h_divuw, u64(quw))
            h_remw = mix(h_remw, u64(rw))
            h_remuw = mix(h_remuw, u64(ruw))
            iters += 1

    for a in EDGE_S64:
        for b in EDGE_S64:
            if b == 0:
                q = -1
                r = a
            elif a == MIN_S64 and b == -1:
                q = MIN_S64
                r = 0
            else:
                q = trunc_div(a, b)
                r = trunc_rem(a, b)

            h_div = mix(h_div, u64(q))
            h_rem = mix(h_rem, u64(r))
            iters += 1

    for a in EDGE_U64:
        for b in EDGE_U64:
            q = MASK64 if b == 0 else (a // b)
            r = a if b == 0 else (a % b)
            h_divu = mix(h_divu, q)
            h_remu = mix(h_remu, r)
            iters += 1

    for a in EDGE_S32:
        for b in EDGE_S32:
            if b == 0:
                q = -1
                r = a
            elif a == MIN_S32 and b == -1:
                q = MIN_S32
                r = 0
            else:
                q = trunc_div(a, b)
                r = trunc_rem(a, b)

            au = u32(a)
            bu = u32(b)
            qu_bits = MASK32 if bu == 0 else (au // bu)
            ru_bits = au if bu == 0 else (au % bu)
            qu = s32(qu_bits)
            ru = s32(ru_bits)

            h_divw = mix(h_divw, u64(q))
            h_divuw = mix(h_divuw, u64(qu))
            h_remw = mix(h_remw, u64(r))
            h_remuw = mix(h_remuw, u64(ru))
            iters += 1

    return (
        h_div,
        h_divu,
        h_rem,
        h_remu,
        h_divw,
        h_divuw,
        h_remw,
        h_remuw,
        iters,
    )


def expected_directed_words() -> tuple[int, ...]:
    dep_q1 = 123456789012345 // 97
    dep_q2 = dep_q1 // 3
    dep_r2 = dep_q2 % 11

    return (
        14,
        2,
        0x5555_5555_5555_5555,
        0,
        0x8000_0000_0000_0000,
        0,
        MASK64,
        77,
        u64(-4),
        u64(-1),
        0x0000_0000_5555_5554,
        2,
        dep_q1,
        dep_q2,
        dep_r2,
        u64(dep_q1 ^ ((dep_q2 << 1) & MASK64) ^ ((dep_r2 << 32) & MASK64)),
        u64(MIN_S32),
        0,
    )


@cocotb.test()
async def test_division_directed_c_program(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    expected = expected_directed_words()

    with tempfile.TemporaryDirectory(prefix="wisp-rv64-division-directed-") as tmpdir:
        artifacts = build_rv64_program(
            source=THIS_DIR / "programs" / "division_directed.c",
            linker_script=THIS_DIR / "linker" / "rv64.ld",
            output_dir=Path(tmpdir),
            march=DEFAULT_MARCH,
            mabi=DEFAULT_MABI,
            extra_gcc_flags=("-O2", "-std=gnu11"),
        )

        image = load_elf_image(artifacts.elf_path)
        await reset_and_load_elf(
            dut,
            image,
            reset_cycles=2,
            clear_words=4096,
            load_imem=True,
            load_dmem=True,
        )

        run = await run_until_termination(
            dut,
            max_cycles=1_000_000,
            tohost_addr=TOHOST_ADDR,
            expected_tohost=1,
            tohost_drain_cycles=8,
            halt_repeat_cycles=512,
        )

        assert run.tohost == 1, (
            f"division_directed: completion mismatch (tohost={run.tohost}) "
            f"reason={run.reason} recent_if_pcs={[hex(pc) for pc in run.recent_if_pcs]}"
        )

        observed = []
        for idx in range(len(expected)):
            observed.append(await tb_read_u64(dut, RESULT_BASE_DIRECTED + (idx * 8)))

        for idx, (got, exp) in enumerate(zip(observed, expected, strict=True)):
            assert got == exp, (
                f"division_directed: mismatch at result[{idx}] "
                f"expected=0x{exp:016x} got=0x{got:016x}"
            )


@cocotb.test()
async def test_division_directed_asm_program(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    expected = expected_directed_words()

    with tempfile.TemporaryDirectory(
        prefix="wisp-rv64-division-directed-asm-"
    ) as tmpdir:
        artifacts = build_rv64_program(
            source=THIS_DIR / "programs" / "division_directed_asm.S",
            linker_script=THIS_DIR / "linker" / "rv64.ld",
            output_dir=Path(tmpdir),
            march=DEFAULT_MARCH,
            mabi=DEFAULT_MABI,
        )

        image = load_elf_image(artifacts.elf_path)
        await reset_and_load_elf(
            dut,
            image,
            reset_cycles=2,
            clear_words=4096,
            load_imem=True,
            load_dmem=True,
        )

        run = await run_until_termination(
            dut,
            max_cycles=1_000_000,
            tohost_addr=TOHOST_ADDR,
            expected_tohost=1,
            tohost_drain_cycles=8,
            halt_repeat_cycles=512,
        )

        assert run.tohost == 1, (
            f"division_directed_asm: completion mismatch (tohost={run.tohost}) "
            f"reason={run.reason} recent_if_pcs={[hex(pc) for pc in run.recent_if_pcs]}"
        )

        observed = []
        for idx in range(len(expected)):
            observed.append(await tb_read_u64(dut, RESULT_BASE_DIRECTED + (idx * 8)))

        for idx, (got, exp) in enumerate(zip(observed, expected, strict=True)):
            assert got == exp, (
                f"division_directed_asm: mismatch at result[{idx}] "
                f"expected=0x{exp:016x} got=0x{got:016x}"
            )


@cocotb.test()
async def test_division_exhaustive_c_program(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    expected = expected_hashes()

    with tempfile.TemporaryDirectory(prefix="wisp-rv64-division-exhaustive-") as tmpdir:
        artifacts = build_rv64_program(
            source=THIS_DIR / "programs" / "division_exhaustive.c",
            linker_script=THIS_DIR / "linker" / "rv64.ld",
            output_dir=Path(tmpdir),
            march=DEFAULT_MARCH,
            mabi=DEFAULT_MABI,
            extra_gcc_flags=("-O2", "-std=gnu11"),
        )

        image = load_elf_image(artifacts.elf_path)
        await reset_and_load_elf(
            dut,
            image,
            reset_cycles=2,
            clear_words=4096,
            load_imem=True,
            load_dmem=True,
        )

        run = await run_until_termination(
            dut,
            max_cycles=8_000_000,
            tohost_addr=TOHOST_ADDR,
            expected_tohost=1,
            tohost_drain_cycles=8,
            halt_repeat_cycles=512,
        )

        assert run.tohost == 1, (
            f"division_exhaustive: completion mismatch (tohost={run.tohost}) "
            f"reason={run.reason} recent_if_pcs={[hex(pc) for pc in run.recent_if_pcs]}"
        )

        observed = []
        for idx in range(9):
            observed.append(await tb_read_u64(dut, RESULT_BASE + (idx * 8)))

        for idx, (got, exp) in enumerate(zip(observed, expected, strict=True)):
            assert got == exp, (
                f"division_exhaustive: mismatch at result[{idx}] "
                f"expected=0x{exp:016x} got=0x{got:016x}"
            )

        retired = len(run.retire_pcs)
        cpi = run.cycles / float(retired) if retired else 0.0
        dut._log.info(
            "division_exhaustive complete: cycles=%d retired=%d CPI=%.4f hash0=0x%016x hash7=0x%016x",
            run.cycles,
            retired,
            cpi,
            observed[0],
            observed[7],
        )
