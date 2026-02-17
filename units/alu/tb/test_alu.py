import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

OPS = {
    "ADD": 0x0,
    "SUB": 0x1,
    "AND": 0x2,
    "OR": 0x3,
    "XOR": 0x4,
    "SLT": 0x5,
    "SLTU": 0x6,
    "SLL": 0x7,
    "SRL": 0x8,
    "SRA": 0x9,
}


def to_u64(value: int) -> int:
    return value & MASK64


def to_s64(value: int) -> int:
    value &= MASK64
    if value & (1 << 63):
        return value - (1 << 64)
    return value


def model(op_name: str, a: int, b: int) -> int:
    a = to_u64(a)
    b = to_u64(b)
    shamt = b & 0x3F

    if op_name == "ADD":
        return to_u64(a + b)
    if op_name == "SUB":
        return to_u64(a - b)
    if op_name == "AND":
        return a & b
    if op_name == "OR":
        return a | b
    if op_name == "XOR":
        return a ^ b
    if op_name == "SLT":
        return 1 if to_s64(a) < to_s64(b) else 0
    if op_name == "SLTU":
        return 1 if a < b else 0
    if op_name == "SLL":
        return to_u64(a << shamt)
    if op_name == "SRL":
        return a >> shamt
    if op_name == "SRA":
        return to_u64(to_s64(a) >> shamt)

    raise ValueError(f"Unknown op: {op_name}")


async def check_op(dut, op_name: str, a: int, b: int) -> None:
    expected = model(op_name, a, b)
    dut.a.value = to_u64(a)
    dut.b.value = to_u64(b)
    dut.op.value = OPS[op_name]
    await Timer(1, unit="ns")

    got = int(dut.result.value)
    zero = int(dut.zero.value)
    expected_zero = 1 if expected == 0 else 0

    assert got == expected, (
        f"{op_name} mismatch: a=0x{a & MASK64:016x} b=0x{b & MASK64:016x} "
        f"expected=0x{expected:016x} got=0x{got:016x}"
    )
    assert zero == expected_zero, (
        f"zero flag mismatch for {op_name}: expected {expected_zero}, got {zero}"
    )


@cocotb.test()
async def test_alu(dut):
    random.seed(64)

    directed = [
        ("ADD", 0, 0),
        ("ADD", MASK64, 1),
        ("SUB", 0, 1),
        ("AND", 0xF0F0, 0x0FF0),
        ("OR", 0x1000, 0x0011),
        ("XOR", 0xAAAA, 0x5555),
        ("SLT", 0xFFFF_FFFF_FFFF_FFFF, 0),
        ("SLT", 0x7FFF_FFFF_FFFF_FFFF, 0x8000_0000_0000_0000),
        ("SLTU", 0, MASK64),
        ("SLL", 1, 63),
        ("SRL", 0x8000_0000_0000_0000, 63),
        ("SRA", 0x8000_0000_0000_0000, 63),
    ]

    for op_name, a, b in directed:
        await check_op(dut, op_name, a, b)

    for op_name in OPS:
        for _ in range(100):
            a = random.getrandbits(64)
            b = random.getrandbits(64)
            await check_op(dut, op_name, a, b)
