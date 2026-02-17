import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

OP = 0b0110011
OP_32 = 0b0111011
F7_M_EXT = 0b0000001

F3_DIV = 0b100
F3_DIVU = 0b101
F3_REM = 0b110
F3_REMU = 0b111


def u64(value: int) -> int:
    return value & MASK64


def s64(value: int) -> int:
    value &= MASK64
    if value & (1 << 63):
        return value - (1 << 64)
    return value


def u32(value: int) -> int:
    return value & 0xFFFF_FFFF


def s32(value: int) -> int:
    value &= 0xFFFF_FFFF
    if value & 0x8000_0000:
        return value - (1 << 32)
    return value


def sext32(value: int) -> int:
    value &= 0xFFFF_FFFF
    if value & 0x8000_0000:
        return value | (~0xFFFF_FFFF & MASK64)
    return value


def trunc_div(a: int, b: int) -> int:
    sign = -1 if ((a < 0) ^ (b < 0)) else 1
    return sign * (abs(a) // abs(b))


def trunc_rem(a: int, b: int) -> int:
    return a - trunc_div(a, b) * b


def model_div(
    opcode: int,
    funct3: int,
    funct7: int,
    rs1_data: int,
    rs2_data: int,
) -> tuple[int, int]:
    if funct7 != F7_M_EXT:
        return 0, 0

    rs1_u = u64(rs1_data)
    rs2_u = u64(rs2_data)
    rs1_s = s64(rs1_data)
    rs2_s = s64(rs2_data)

    if opcode == OP:
        if funct3 == F3_DIV:
            if rs2_u == 0:
                return 1, MASK64
            if rs1_u == 0x8000_0000_0000_0000 and rs2_u == MASK64:
                return 1, 0x8000_0000_0000_0000
            return 1, u64(trunc_div(rs1_s, rs2_s))

        if funct3 == F3_DIVU:
            if rs2_u == 0:
                return 1, MASK64
            return 1, u64(rs1_u // rs2_u)

        if funct3 == F3_REM:
            if rs2_u == 0:
                return 1, rs1_u
            if rs1_u == 0x8000_0000_0000_0000 and rs2_u == MASK64:
                return 1, 0
            return 1, u64(trunc_rem(rs1_s, rs2_s))

        if funct3 == F3_REMU:
            if rs2_u == 0:
                return 1, rs1_u
            return 1, u64(rs1_u % rs2_u)

        return 0, 0

    if opcode == OP_32:
        rs1_w_u = u32(rs1_data)
        rs2_w_u = u32(rs2_data)
        rs1_w_s = s32(rs1_data)
        rs2_w_s = s32(rs2_data)

        if funct3 == F3_DIV:
            if rs2_w_u == 0:
                return 1, MASK64
            if rs1_w_u == 0x8000_0000 and rs2_w_u == 0xFFFF_FFFF:
                return 1, 0xFFFF_FFFF_8000_0000
            return 1, sext32(trunc_div(rs1_w_s, rs2_w_s))

        if funct3 == F3_DIVU:
            if rs2_w_u == 0:
                return 1, MASK64
            return 1, sext32(rs1_w_u // rs2_w_u)

        if funct3 == F3_REM:
            if rs2_w_u == 0:
                return 1, sext32(rs1_w_u)
            if rs1_w_u == 0x8000_0000 and rs2_w_u == 0xFFFF_FFFF:
                return 1, 0
            return 1, sext32(trunc_rem(rs1_w_s, rs2_w_s))

        if funct3 == F3_REMU:
            if rs2_w_u == 0:
                return 1, sext32(rs1_w_u)
            return 1, sext32(rs1_w_u % rs2_w_u)

        return 0, 0

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

    exp_valid, exp_result = model_div(opcode, funct3, funct7, rs1_data, rs2_data)
    got_valid = int(dut.op_valid.value)
    got_result = int(dut.result.value) & MASK64

    assert got_valid == exp_valid, (
        f"{name}: op_valid expected {exp_valid} got {got_valid}"
    )
    assert got_result == exp_result, (
        f"{name}: result expected 0x{exp_result:016x} got 0x{got_result:016x}"
    )


@cocotb.test()
async def test_div_unit_directed(dut):
    vectors = [
        {
            "name": "DIV_SIGNED",
            "opcode": OP,
            "funct3": F3_DIV,
            "funct7": F7_M_EXT,
            "rs1_data": 100,
            "rs2_data": 7,
        },
        {
            "name": "DIV_SIGNED_BY_ZERO",
            "opcode": OP,
            "funct3": F3_DIV,
            "funct7": F7_M_EXT,
            "rs1_data": 77,
            "rs2_data": 0,
        },
        {
            "name": "DIV_SIGNED_OVERFLOW",
            "opcode": OP,
            "funct3": F3_DIV,
            "funct7": F7_M_EXT,
            "rs1_data": 0x8000_0000_0000_0000,
            "rs2_data": -1,
        },
        {
            "name": "DIVU_UNSIGNED",
            "opcode": OP,
            "funct3": F3_DIVU,
            "funct7": F7_M_EXT,
            "rs1_data": 0xFFFF_FFFF_FFFF_FFFF,
            "rs2_data": 3,
        },
        {
            "name": "REM_SIGNED",
            "opcode": OP,
            "funct3": F3_REM,
            "funct7": F7_M_EXT,
            "rs1_data": -9,
            "rs2_data": 2,
        },
        {
            "name": "REMU_UNSIGNED",
            "opcode": OP,
            "funct3": F3_REMU,
            "funct7": F7_M_EXT,
            "rs1_data": 0xFFFF_FFFF_FFFF_FFFF,
            "rs2_data": 3,
        },
        {
            "name": "DIVW_SIGNED",
            "opcode": OP_32,
            "funct3": F3_DIV,
            "funct7": F7_M_EXT,
            "rs1_data": -9,
            "rs2_data": 2,
        },
        {
            "name": "DIVW_OVERFLOW",
            "opcode": OP_32,
            "funct3": F3_DIV,
            "funct7": F7_M_EXT,
            "rs1_data": 0xFFFF_FFFF_8000_0000,
            "rs2_data": -1,
        },
        {
            "name": "DIVUW_UNSIGNED",
            "opcode": OP_32,
            "funct3": F3_DIVU,
            "funct7": F7_M_EXT,
            "rs1_data": 0xFFFF_FFFF_FFFF_FFFE,
            "rs2_data": 3,
        },
        {
            "name": "REMW_SIGNED",
            "opcode": OP_32,
            "funct3": F3_REM,
            "funct7": F7_M_EXT,
            "rs1_data": -9,
            "rs2_data": 2,
        },
        {
            "name": "REMUW_UNSIGNED",
            "opcode": OP_32,
            "funct3": F3_REMU,
            "funct7": F7_M_EXT,
            "rs1_data": 0xFFFF_FFFF_FFFF_FFFE,
            "rs2_data": 3,
        },
        {
            "name": "BAD_FUNCT7",
            "opcode": OP,
            "funct3": F3_DIV,
            "funct7": 0,
            "rs1_data": 10,
            "rs2_data": 3,
        },
    ]

    for vec in vectors:
        await check_case(dut, **vec)


@cocotb.test()
async def test_div_unit_randomized(dut):
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
