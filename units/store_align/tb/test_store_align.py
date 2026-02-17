import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

F3_SB = 0b000
F3_SH = 0b001
F3_SW = 0b010
F3_SD = 0b011


def model_store_align(rs2_data: int, addr_lsb: int, funct3: int) -> tuple[int, int]:
    shift = (addr_lsb & 0x7) * 8

    if funct3 == F3_SB:
        store_data = ((rs2_data & 0xFF) << shift) & MASK64
        byte_en = (0x01 << (addr_lsb & 0x7)) & 0xFF
        return store_data, byte_en

    if funct3 == F3_SH:
        store_data = ((rs2_data & 0xFFFF) << shift) & MASK64
        byte_en = (0x03 << (addr_lsb & 0x7)) & 0xFF
        return store_data, byte_en

    if funct3 == F3_SW:
        store_data = ((rs2_data & 0xFFFF_FFFF) << shift) & MASK64
        byte_en = (0x0F << (addr_lsb & 0x7)) & 0xFF
        return store_data, byte_en

    if funct3 == F3_SD:
        return rs2_data & MASK64, 0xFF

    return 0, 0


async def check_case(dut, rs2_data: int, addr_lsb: int, funct3: int, name: str) -> None:
    dut.rs2_data.value = rs2_data & MASK64
    dut.addr_lsb.value = addr_lsb & 0x7
    dut.funct3.value = funct3 & 0x7
    await Timer(1, unit="ns")

    exp_data, exp_be = model_store_align(rs2_data, addr_lsb, funct3)
    got_data = int(dut.store_data.value) & MASK64
    got_be = int(dut.byte_en.value) & 0xFF

    assert got_data == exp_data, (
        f"{name}: store_data mismatch expected=0x{exp_data:016x} got=0x{got_data:016x}"
    )
    assert got_be == exp_be, (
        f"{name}: byte_en mismatch expected=0b{exp_be:08b} got=0b{got_be:08b}"
    )


@cocotb.test()
async def test_store_align_directed(dut):
    vectors = [
        ("SB_OFF0", 0x0123_4567_89AB_CDEF, 0, F3_SB),
        ("SB_OFF7", 0x0123_4567_89AB_CDEF, 7, F3_SB),
        ("SH_OFF2", 0x0123_4567_89AB_CDEF, 2, F3_SH),
        ("SH_OFF6", 0x0123_4567_89AB_CDEF, 6, F3_SH),
        ("SW_OFF1", 0x0123_4567_89AB_CDEF, 1, F3_SW),
        ("SW_OFF4", 0x0123_4567_89AB_CDEF, 4, F3_SW),
        ("SD", 0x0123_4567_89AB_CDEF, 3, F3_SD),
        ("INVALID_FUNCT3", 0x0123_4567_89AB_CDEF, 0, 0b111),
    ]

    for name, rs2_data, addr_lsb, funct3 in vectors:
        await check_case(dut, rs2_data, addr_lsb, funct3, name)


@cocotb.test()
async def test_store_align_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        rs2_data = random.getrandbits(64)
        addr_lsb = random.getrandbits(3)
        funct3 = random.getrandbits(3)
        await check_case(dut, rs2_data, addr_lsb, funct3, f"RAND_{idx}")
