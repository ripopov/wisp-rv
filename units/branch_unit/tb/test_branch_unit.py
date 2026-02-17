import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

F3_BEQ = 0b000
F3_BNE = 0b001
F3_BLT = 0b100
F3_BGE = 0b101
F3_BLTU = 0b110
F3_BGEU = 0b111


def as_signed_64(value: int) -> int:
    value &= MASK64
    if value & (1 << 63):
        return value - (1 << 64)
    return value


def model_branch_taken(rs1_data: int, rs2_data: int, funct3: int, branch: int) -> int:
    if not branch:
        return 0

    rs1_u = rs1_data & MASK64
    rs2_u = rs2_data & MASK64
    rs1_s = as_signed_64(rs1_data)
    rs2_s = as_signed_64(rs2_data)

    if funct3 == F3_BEQ:
        return int(rs1_u == rs2_u)
    if funct3 == F3_BNE:
        return int(rs1_u != rs2_u)
    if funct3 == F3_BLT:
        return int(rs1_s < rs2_s)
    if funct3 == F3_BGE:
        return int(rs1_s >= rs2_s)
    if funct3 == F3_BLTU:
        return int(rs1_u < rs2_u)
    if funct3 == F3_BGEU:
        return int(rs1_u >= rs2_u)
    return 0


async def check_case(
    dut, rs1_data: int, rs2_data: int, funct3: int, branch: int, name: str
) -> None:
    dut.rs1_data.value = rs1_data & MASK64
    dut.rs2_data.value = rs2_data & MASK64
    dut.funct3.value = funct3 & 0x7
    dut.branch.value = branch
    await Timer(1, unit="ns")

    expected = model_branch_taken(rs1_data, rs2_data, funct3, branch)
    got = int(dut.branch_taken.value)
    assert got == expected, (
        f"{name}: rs1=0x{rs1_data & MASK64:016x} rs2=0x{rs2_data & MASK64:016x} "
        f"funct3={funct3:03b} branch={branch} expected={expected} got={got}"
    )


@cocotb.test()
async def test_branch_unit_directed(dut):
    max_pos = 0x7FFF_FFFF_FFFF_FFFF
    min_neg = 0x8000_0000_0000_0000
    max_u = 0xFFFF_FFFF_FFFF_FFFF

    vectors = [
        ("BEQ_TRUE", 0x1234, 0x1234, F3_BEQ, 1),
        ("BEQ_FALSE", 0x1234, 0x5678, F3_BEQ, 1),
        ("BNE_TRUE", 0x1234, 0x5678, F3_BNE, 1),
        ("BNE_FALSE", 0x1234, 0x1234, F3_BNE, 1),
        ("BLT_SIGNED_TRUE", min_neg, max_pos, F3_BLT, 1),
        ("BLT_SIGNED_FALSE", max_pos, min_neg, F3_BLT, 1),
        ("BGE_SIGNED_TRUE", max_pos, min_neg, F3_BGE, 1),
        ("BGE_SIGNED_FALSE", min_neg, max_pos, F3_BGE, 1),
        ("BLTU_TRUE", 0, max_u, F3_BLTU, 1),
        ("BLTU_FALSE", max_u, max_u - 1, F3_BLTU, 1),
        ("BGEU_TRUE", max_u, max_u - 1, F3_BGEU, 1),
        ("BGEU_FALSE", 0, max_u, F3_BGEU, 1),
        ("INVALID_FUNCT3", 0xAA, 0xBB, 0b010, 1),
        ("BRANCH_DISABLED", 0xAA, 0xAA, F3_BEQ, 0),
    ]

    for name, rs1_data, rs2_data, funct3, branch in vectors:
        await check_case(dut, rs1_data, rs2_data, funct3, branch, name)


@cocotb.test()
async def test_branch_unit_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        rs1_data = random.getrandbits(64)
        rs2_data = random.getrandbits(64)
        funct3 = random.getrandbits(3)
        branch = random.getrandbits(1)
        await check_case(dut, rs1_data, rs2_data, funct3, branch, f"RAND_{idx}")
