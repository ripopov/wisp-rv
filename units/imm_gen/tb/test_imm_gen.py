import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

FMT_R = 0
FMT_I = 1
FMT_S = 2
FMT_B = 3
FMT_U = 4
FMT_J = 5


def sign_extend(value: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    value &= (1 << bits) - 1
    if value & sign_bit:
        value -= 1 << bits
    return value & MASK64


def enc_i(imm12: int) -> int:
    return (imm12 & 0xFFF) << 20


def enc_s(imm12: int) -> int:
    imm12 &= 0xFFF
    return (((imm12 >> 5) & 0x7F) << 25) | ((imm12 & 0x1F) << 7)


def enc_b(imm13: int) -> int:
    imm13 &= 0x1FFF
    return (
        (((imm13 >> 12) & 0x1) << 31)
        | (((imm13 >> 5) & 0x3F) << 25)
        | (((imm13 >> 1) & 0xF) << 8)
        | (((imm13 >> 11) & 0x1) << 7)
    )


def enc_u(imm20: int) -> int:
    return (imm20 & 0xFFFFF) << 12


def enc_j(imm21: int) -> int:
    imm21 &= 0x1FFFFF
    return (
        (((imm21 >> 20) & 0x1) << 31)
        | (((imm21 >> 1) & 0x3FF) << 21)
        | (((imm21 >> 11) & 0x1) << 20)
        | (((imm21 >> 12) & 0xFF) << 12)
    )


def model_imm(instr: int, instr_format: int) -> int:
    if instr_format == FMT_I:
        imm12 = (instr >> 20) & 0xFFF
        return sign_extend(imm12, 12)
    if instr_format == FMT_S:
        imm12 = ((instr >> 25) << 5) | ((instr >> 7) & 0x1F)
        return sign_extend(imm12, 12)
    if instr_format == FMT_B:
        imm13 = (
            (((instr >> 31) & 0x1) << 12)
            | (((instr >> 7) & 0x1) << 11)
            | (((instr >> 25) & 0x3F) << 5)
            | (((instr >> 8) & 0xF) << 1)
        )
        return sign_extend(imm13, 13)
    if instr_format == FMT_U:
        imm32 = instr & 0xFFFFF000
        return sign_extend(imm32, 32)
    if instr_format == FMT_J:
        imm21 = (
            (((instr >> 31) & 0x1) << 20)
            | (((instr >> 12) & 0xFF) << 12)
            | (((instr >> 20) & 0x1) << 11)
            | (((instr >> 21) & 0x3FF) << 1)
        )
        return sign_extend(imm21, 21)
    return 0


async def check_case(
    dut, instr: int, instr_format: int, expected: int, name: str
) -> None:
    dut.instr.value = instr & 0xFFFF_FFFF
    dut.instr_format.value = instr_format
    await Timer(1, unit="ns")

    got = int(dut.imm.value) & MASK64
    assert got == (expected & MASK64), (
        f"{name}: instr=0x{instr:08x} format={instr_format} expected=0x{expected & MASK64:016x} got=0x{got:016x}"
    )


@cocotb.test()
async def test_directed_immediate_vectors(dut):
    vectors = [
        ("I_ZERO", enc_i(0x000), FMT_I),
        ("I_MAX_POS", enc_i(0x7FF), FMT_I),
        ("I_MIN_NEG", enc_i(0x800), FMT_I),
        ("S_ZERO", enc_s(0x000), FMT_S),
        ("S_MAX_POS", enc_s(0x7FF), FMT_S),
        ("S_MIN_NEG", enc_s(0x800), FMT_S),
        ("B_ZERO", enc_b(0x000), FMT_B),
        ("B_MAX_POS", enc_b(0x0FFE), FMT_B),
        ("B_MIN_NEG", enc_b(0x1000), FMT_B),
        ("U_POS", enc_u(0x7FFFF), FMT_U),
        ("U_NEG", enc_u(0x80000), FMT_U),
        ("J_ZERO", enc_j(0x00000), FMT_J),
        ("J_POS", enc_j(0x000FE), FMT_J),
        ("J_NEG", enc_j(0x1FFFFE), FMT_J),
        ("R_TYPE_UNUSED", 0xFFFF_FFFF, FMT_R),
    ]

    for name, instr, instr_format in vectors:
        expected = model_imm(instr, instr_format)
        await check_case(dut, instr, instr_format, expected, name)


@cocotb.test()
async def test_randomized_immediates(dut):
    random.seed(64)
    formats = [FMT_R, FMT_I, FMT_S, FMT_B, FMT_U, FMT_J]

    for _ in range(10_000):
        instr = random.getrandbits(32)
        instr_format = random.choice(formats)
        expected = model_imm(instr, instr_format)
        await check_case(dut, instr, instr_format, expected, "RAND")
