from pathlib import Path
import sys

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from utils.build_rv64_program import (
    DEFAULT_MABI,
    DEFAULT_MARCH,
    build_rv64_program_u32_words,
)

MASK64 = (1 << 64) - 1
TOHOST_ADDR = 0x200
SYSTEM = 0b1110011
AFTER_ILLEGAL_PC = 0x58
AFTER_ECALL_PC = 0x74
AFTER_RO_WRITE_PC = 0xA8


def enc_i(imm12: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    return (
        ((imm12 & 0xFFF) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def init_tb_ports(dut) -> None:
    dut.tb_mem_wr_en.value = 0
    dut.tb_mem_is_data.value = 1
    dut.tb_mem_wr_addr.value = 0
    dut.tb_mem_wr_data.value = 0
    dut.tb_mem_wr_be.value = 0
    dut.tb_mem_rd_addr.value = 0


async def tb_write_word(
    dut,
    word_idx: int,
    value: int,
    be: int = 0xFF,
    *,
    is_data: bool = True,
) -> None:
    dut.tb_mem_is_data.value = 1 if is_data else 0
    dut.tb_mem_wr_addr.value = (word_idx << 3) & MASK64
    dut.tb_mem_wr_data.value = value & MASK64
    dut.tb_mem_wr_be.value = be & 0xFF
    dut.tb_mem_wr_en.value = 1
    await RisingEdge(dut.clk)
    dut.tb_mem_wr_en.value = 0


async def tb_read_word(dut, word_idx: int, *, is_data: bool = True) -> int:
    dut.tb_mem_is_data.value = 1 if is_data else 0
    dut.tb_mem_rd_addr.value = (word_idx << 3) & MASK64
    await Timer(1, unit="ns")
    return int(dut.tb_mem_rd_data.value) & MASK64


async def tb_read_u64(dut, addr: int, *, is_data: bool = True) -> int:
    assert (addr & 0x7) == 0
    return await tb_read_word(dut, addr >> 3, is_data=is_data)


async def write_instr_u32(dut, byte_addr: int, instr: int) -> None:
    word_idx = byte_addr >> 3
    lane = (byte_addr >> 2) & 0x1
    if lane == 0:
        wdata = instr & 0xFFFF_FFFF
        be = 0x0F
    else:
        wdata = (instr & 0xFFFF_FFFF) << 32
        be = 0xF0
    await tb_write_word(dut, word_idx, wdata, be, is_data=False)


async def clear_ram_prefix(dut, words: int = 512) -> None:
    for idx in range(words):
        await tb_write_word(dut, idx, 0, 0xFF, is_data=False)
        await tb_write_word(dut, idx, 0, 0xFF, is_data=True)


async def load_program_into_ram(dut, program_words: dict[int, int]) -> None:
    for word_idx, instr in program_words.items():
        await write_instr_u32(dut, word_idx * 4, instr)


def build_program() -> dict[int, int]:
    root = Path(__file__).resolve().parent
    src = root / "programs" / "stage9_smoke.S"
    linker = root / "linker" / "rv64.ld"
    return build_rv64_program_u32_words(
        src,
        linker,
        march=DEFAULT_MARCH,
        mabi=DEFAULT_MABI,
    )


async def reset_dut_with_program(
    dut, program_words: dict[int, int], cycles: int = 2
) -> None:
    dut.rst.value = 1
    await ClockCycles(dut.clk, cycles)
    await clear_ram_prefix(dut)
    await load_program_into_ram(dut, program_words)
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def run_until_completion(dut, *, max_cycles: int) -> None:
    tohost_seen = False
    drain_cycles = 0
    recent_pcs: list[int] = []

    for _ in range(max_cycles):
        await RisingEdge(dut.clk)

        recent_pcs.append(int(dut.dbg_if_pc.value) & MASK64)
        if len(recent_pcs) > 24:
            recent_pcs.pop(0)

        if (await tb_read_u64(dut, TOHOST_ADDR)) != 0 and not tohost_seen:
            tohost_seen = True
            drain_cycles = 8

        if tohost_seen:
            drain_cycles -= 1
            if drain_cycles == 0:
                return

    raise AssertionError(
        "Program did not complete before timeout"
        f"; recent_pcs={[hex(pc) for pc in recent_pcs]}"
    )


@cocotb.test()
async def test_stage9_program_end_to_end(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    program_words = build_program()
    await reset_dut_with_program(dut, program_words)
    await run_until_completion(dut, max_cycles=25_000)

    observed = {}
    for addr in (
        TOHOST_ADDR,
        0x100,
        0x108,
        0x110,
        0x118,
        0x120,
        0x128,
        0x130,
        0x138,
        0x140,
        0x148,
        0x150,
        0x158,
        0x160,
        0x168,
        0x170,
        0x178,
        0x180,
        0x188,
        0x190,
        0x198,
        0x1A0,
        0x1A8,
        0x1B0,
        0x1B8,
        0x1C0,
        0x1C8,
        0x1D0,
        0x1D8,
        0x1E0,
        0x1E8,
        0x1F0,
        0x1F8,
        0x210,
        0x218,
        0x220,
        0x228,
        0x230,
    ):
        observed[addr] = await tb_read_u64(dut, addr)

    assert observed[TOHOST_ADDR] == 1
    assert observed[0x100] == 15
    assert observed[0x108] == 0
    assert observed[0x110] == 0x8
    assert observed[0x118] == 0
    assert observed[0x120] == 0x80
    assert observed[0x128] == 0x80

    assert observed[0x130] == 2
    assert observed[0x138] == AFTER_ILLEGAL_PC
    assert observed[0x140] == 0

    assert observed[0x148] == 11
    assert observed[0x150] == AFTER_ECALL_PC
    assert observed[0x158] == 0
    assert observed[0x160] == 2

    mcycle = observed[0x168]
    minstret = observed[0x170]
    assert mcycle > 0
    assert minstret > 0
    assert mcycle >= minstret

    expected_ro_write_mtval = enc_i(0xF11, 1, 0b001, 19, SYSTEM)
    assert observed[0x178] == 2
    assert observed[0x180] == AFTER_RO_WRITE_PC
    assert observed[0x188] == expected_ro_write_mtval
    assert observed[0x190] == 3

    assert observed[0x198] == 42
    assert observed[0x1A0] == 0xFFFF_FFFF_FFFF_FFFF
    assert observed[0x1A8] == 0xFFFF_FFFF_FFFF_FFFF
    assert observed[0x1B0] == 1
    assert observed[0x1B8] == 0xFFFF_FFFF_FFFF_FFFE

    assert observed[0x1C0] == 14
    assert observed[0x1C8] == 0xFFFF_FFFF_FFFF_FFFF
    assert observed[0x1D0] == 0x8000_0000_0000_0000
    assert observed[0x1D8] == 0x5555_5555_5555_5555
    assert observed[0x1E0] == 0xFFFF_FFFF_FFFF_FFFF
    assert observed[0x1E8] == 0
    assert observed[0x1F0] == 0xFFFF_FFFF_FFFF_FFFC
    assert observed[0x1F8] == 0x0000_0000_5555_5554
    assert observed[0x210] == 0xFFFF_FFFF_FFFF_FFFF
    assert observed[0x218] == 0xFFFF_FFFF_FFFF_FFFF
    assert observed[0x220] == 2
    assert observed[0x228] == 0xFFFF_FFFF_FFFF_FFFE
    assert observed[0x230] == 15
