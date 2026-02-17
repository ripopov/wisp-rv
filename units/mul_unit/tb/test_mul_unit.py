import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

OP = 0b0110011
OP_32 = 0b0111011
F7_M_EXT = 0b0000001

F3_MUL = 0b000
F3_MULH = 0b001
F3_MULHSU = 0b010
F3_MULHU = 0b011


def u64(value: int) -> int:
    return value & MASK64


def s64(value: int) -> int:
    value &= MASK64
    if value & (1 << 63):
        return value - (1 << 64)
    return value


def sext32(value: int) -> int:
    value &= 0xFFFF_FFFF
    if value & 0x8000_0000:
        return value | (~0xFFFF_FFFF & MASK64)
    return value


def model_mul(
    opcode: int,
    funct3: int,
    funct7: int,
    rs1_data: int,
    rs2_data: int,
) -> tuple[int, int]:
    if funct7 != F7_M_EXT:
        return 0, 0

    if opcode == OP:
        if funct3 == F3_MUL:
            return 1, u64(u64(rs1_data) * u64(rs2_data))

        if funct3 == F3_MULH:
            prod = s64(rs1_data) * s64(rs2_data)
            return 1, u64(prod >> 64)

        if funct3 == F3_MULHSU:
            prod = s64(rs1_data) * u64(rs2_data)
            return 1, u64(prod >> 64)

        if funct3 == F3_MULHU:
            prod = u64(rs1_data) * u64(rs2_data)
            return 1, u64(prod >> 64)

        return 0, 0

    if opcode == OP_32 and funct3 == F3_MUL:
        prod = (rs1_data & 0xFFFF_FFFF) * (rs2_data & 0xFFFF_FFFF)
        return 1, sext32(prod)

    return 0, 0


async def check_case(
    dut,
    *,
    opcode: int,
    funct3: int,
    funct7: int,
    rs1_data: int,
    rs2_data: int,
    name: str,
) -> None:
    dut.opcode.value = opcode & 0x7F
    dut.funct3.value = funct3 & 0x7
    dut.funct7.value = funct7 & 0x7F
    dut.rs1_data.value = u64(rs1_data)
    dut.rs2_data.value = u64(rs2_data)
    await Timer(1, unit="ns")

    exp_valid, exp_result = model_mul(opcode, funct3, funct7, rs1_data, rs2_data)
    got_valid = int(dut.op_valid.value)
    got_result = int(dut.result.value) & MASK64

    assert got_valid == exp_valid, (
        f"{name}: op_valid expected {exp_valid} got {got_valid}"
    )
    assert got_result == exp_result, (
        f"{name}: result expected 0x{exp_result:016x} got 0x{got_result:016x}"
    )


@cocotb.test()
async def test_mul_unit_directed(dut):
    vectors = [
        {
            "name": "MUL_SIMPLE",
            "opcode": OP,
            "funct3": F3_MUL,
            "funct7": F7_M_EXT,
            "rs1_data": 5,
            "rs2_data": 7,
        },
        {
            "name": "MULH_SIGNED_NEG",
            "opcode": OP,
            "funct3": F3_MULH,
            "funct7": F7_M_EXT,
            "rs1_data": -3,
            "rs2_data": 5,
        },
        {
            "name": "MULHSU_SIGNED_UNSIGNED",
            "opcode": OP,
            "funct3": F3_MULHSU,
            "funct7": F7_M_EXT,
            "rs1_data": -3,
            "rs2_data": 5,
        },
        {
            "name": "MULHU_UNSIGNED_HIGH",
            "opcode": OP,
            "funct3": F3_MULHU,
            "funct7": F7_M_EXT,
            "rs1_data": 0xFFFF_FFFF_FFFF_FFFF,
            "rs2_data": 2,
        },
        {
            "name": "MULW_SIGN_EXT",
            "opcode": OP_32,
            "funct3": F3_MUL,
            "funct7": F7_M_EXT,
            "rs1_data": 0xFFFF_FFFF_FFFF_FFFF,
            "rs2_data": 2,
        },
        {
            "name": "BAD_FUNCT7",
            "opcode": OP,
            "funct3": F3_MUL,
            "funct7": 0b0000000,
            "rs1_data": 9,
            "rs2_data": 9,
        },
        {
            "name": "BAD_OP32_FUNCT3",
            "opcode": OP_32,
            "funct3": 0b001,
            "funct7": F7_M_EXT,
            "rs1_data": 3,
            "rs2_data": 4,
        },
    ]

    for vec in vectors:
        await check_case(dut, **vec)


@cocotb.test()
async def test_mul_unit_randomized(dut):
    random.seed(64)

    opcodes = [OP, OP_32]

    for idx in range(20_000):
        opcode = (
            random.choice(opcodes) if random.getrandbits(1) else random.getrandbits(7)
        )
        await check_case(
            dut,
            name=f"RAND_{idx}",
            opcode=opcode,
            funct3=random.getrandbits(3),
            funct7=random.getrandbits(7),
            rs1_data=random.getrandbits(64),
            rs2_data=random.getrandbits(64),
        )
