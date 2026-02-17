import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1

OP_IMM = 0b0010011
STORE = 0b0100011
JAL = 0b1101111

F3_SD = 0b011

TOHOST_ADDR = 0x200
MARKER_ADDR = 0x208
NOP = 0x00000013


def enc_i(imm12: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    return (
        ((imm12 & 0xFFF) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_s(imm12: int, rs2: int, rs1: int, funct3: int, opcode: int) -> int:
    imm12 &= 0xFFF
    return (
        (((imm12 >> 5) & 0x7F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((imm12 & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_j(offset: int, rd: int, opcode: int) -> int:
    imm21 = offset & 0x1FFFFF
    return (
        (((imm21 >> 20) & 0x1) << 31)
        | (((imm21 >> 1) & 0x3FF) << 21)
        | (((imm21 >> 11) & 0x1) << 20)
        | (((imm21 >> 12) & 0xFF) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def build_store_program(value: int) -> list[int]:
    return [
        enc_i(TOHOST_ADDR, 0, 0b000, 1, OP_IMM),  # addi x1, x0, TOHOST_ADDR
        enc_i(value, 0, 0b000, 2, OP_IMM),  # addi x2, x0, value
        NOP,
        NOP,
        enc_s(0, 2, 1, F3_SD, STORE),  # sd x2, 0(x1)
        enc_i(1, 2, 0b000, 3, OP_IMM),  # addi x3, x2, 1
        NOP,
        NOP,
        enc_s(8, 3, 1, F3_SD, STORE),  # sd x3, 8(x1)
        enc_j(0, 0, JAL),  # jal x0, .
    ]


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


async def tb_read_instr_u32(dut, byte_addr: int) -> int:
    word = await tb_read_word(dut, byte_addr >> 3, is_data=False)
    lane = (byte_addr >> 2) & 0x1
    if lane == 0:
        return word & 0xFFFF_FFFF
    return (word >> 32) & 0xFFFF_FFFF


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


async def clear_program_region(dut, words: int = 96) -> None:
    for idx in range(words):
        await tb_write_word(dut, idx, 0, 0xFF, is_data=False)
        await tb_write_word(dut, idx, 0, 0xFF, is_data=True)


async def load_program(dut, words: list[int]) -> None:
    for idx, instr in enumerate(words):
        await write_instr_u32(dut, idx * 4, instr)


async def prepare_program(dut, words: list[int]) -> None:
    dut.rst.value = 1
    await ClockCycles(dut.clk, 2)
    await clear_program_region(dut)
    await load_program(dut, words)
    await ClockCycles(dut.clk, 2)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def run_until_tohost(dut, expected: int, max_cycles: int = 900) -> None:
    recent_pcs: list[int] = []
    matched = False
    drain_cycles = 0

    for _ in range(max_cycles):
        await RisingEdge(dut.clk)

        recent_pcs.append(int(dut.dbg_if_pc.value) & MASK64)
        if len(recent_pcs) > 24:
            recent_pcs.pop(0)

        tohost = await tb_read_u64(dut, TOHOST_ADDR)
        if (not matched) and (tohost == expected):
            matched = True
            drain_cycles = 8

        if matched:
            drain_cycles -= 1
            if drain_cycles == 0:
                return

    raise AssertionError(
        f"tohost never reached expected value 0x{expected:016x}; "
        f"recent_pcs={[hex(pc) for pc in recent_pcs]}"
    )


@cocotb.test()
async def test_memory_subsystem_directed(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    words = build_store_program(1)
    await prepare_program(dut, words)

    for idx, instr in enumerate(words):
        got = await tb_read_instr_u32(dut, idx * 4)
        assert got == (instr & 0xFFFF_FFFF)

    await run_until_tohost(dut, expected=1)

    assert await tb_read_u64(dut, TOHOST_ADDR) == 1
    assert await tb_read_u64(dut, MARKER_ADDR) == 2


@cocotb.test()
async def test_memory_subsystem_randomized_values(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    random.seed(64)

    for _ in range(12):
        value = random.randint(-2048, 2047)
        if value == 0:
            value = 1

        words = build_store_program(value)
        await prepare_program(dut, words)

        expected_tohost = value & MASK64
        expected_marker = (value + 1) & MASK64

        await run_until_tohost(dut, expected=expected_tohost)
        assert await tb_read_u64(dut, TOHOST_ADDR) == expected_tohost
        assert await tb_read_u64(dut, MARKER_ADDR) == expected_marker
