import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

F3_LB = 0b000
F3_LH = 0b001
F3_LW = 0b010
F3_LD = 0b011
F3_LBU = 0b100
F3_LHU = 0b101
F3_LWU = 0b110


def sign_extend(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        value -= 1 << bits
    return value & MASK64


def model_load_align(mem_rdata: int, addr_lsb: int, funct3: int) -> int:
    shifted = (mem_rdata & MASK64) >> ((addr_lsb & 0x7) * 8)

    if funct3 == F3_LB:
        return sign_extend(shifted, 8)
    if funct3 == F3_LH:
        return sign_extend(shifted, 16)
    if funct3 == F3_LW:
        return sign_extend(shifted, 32)
    if funct3 == F3_LD:
        return shifted & MASK64
    if funct3 == F3_LBU:
        return shifted & 0xFF
    if funct3 == F3_LHU:
        return shifted & 0xFFFF
    if funct3 == F3_LWU:
        return shifted & 0xFFFF_FFFF
    return 0


async def check_case(
    dut, mem_rdata: int, addr_lsb: int, funct3: int, name: str
) -> None:
    dut.mem_rdata.value = mem_rdata & MASK64
    dut.addr_lsb.value = addr_lsb & 0x7
    dut.funct3.value = funct3 & 0x7
    await Timer(1, unit="ns")

    expected = model_load_align(mem_rdata, addr_lsb, funct3)
    got = int(dut.load_data.value) & MASK64
    assert got == expected, (
        f"{name}: mem_rdata=0x{mem_rdata & MASK64:016x} addr_lsb={addr_lsb} "
        f"funct3={funct3:03b} expected=0x{expected:016x} got=0x{got:016x}"
    )


@cocotb.test()
async def test_load_align_directed(dut):
    mem = 0x80FF_7F01_1234_56AB

    vectors = [
        ("LB_SIGN_NEG", mem, 7, F3_LB),
        ("LB_SIGN_POS", mem, 6, F3_LB),
        ("LH_SIGN_NEG", mem, 6, F3_LH),
        ("LH_SIGN_POS", mem, 0, F3_LH),
        ("LW_SIGN_NEG", 0x0000_0000_8000_00FF, 0, F3_LW),
        ("LW_SIGN_POS", 0x0000_0000_7FFF_FF00, 0, F3_LW),
        ("LD_OFFSET0", 0x0123_4567_89AB_CDEF, 0, F3_LD),
        ("LD_OFFSET1", 0x0123_4567_89AB_CDEF, 1, F3_LD),
        ("LBU", mem, 7, F3_LBU),
        ("LHU", mem, 5, F3_LHU),
        ("LWU", 0xFFFF_FFFF_8000_0001, 0, F3_LWU),
        ("INVALID_FUNCT3", mem, 0, 0b111),
    ]

    for name, mem_rdata, addr_lsb, funct3 in vectors:
        await check_case(dut, mem_rdata, addr_lsb, funct3, name)


@cocotb.test()
async def test_load_align_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        mem_rdata = random.getrandbits(64)
        addr_lsb = random.getrandbits(3)
        funct3 = random.getrandbits(3)
        await check_case(dut, mem_rdata, addr_lsb, funct3, f"RAND_{idx}")
