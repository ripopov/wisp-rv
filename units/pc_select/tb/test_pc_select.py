import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1


def model_next_pc(
    current_pc: int, stall: int, redirect_valid: int, redirect_pc: int
) -> int:
    if redirect_valid:
        return redirect_pc & MASK64
    if stall:
        return current_pc & MASK64
    return (current_pc + 4) & MASK64


async def check_case(
    dut,
    current_pc: int,
    stall: int,
    redirect_valid: int,
    redirect_pc: int,
    name: str,
) -> None:
    dut.current_pc.value = current_pc & MASK64
    dut.stall.value = stall
    dut.redirect_valid.value = redirect_valid
    dut.redirect_pc.value = redirect_pc & MASK64
    await Timer(1, unit="ns")

    expected = model_next_pc(current_pc, stall, redirect_valid, redirect_pc)
    got = int(dut.next_pc.value) & MASK64
    assert got == expected, (
        f"{name}: current_pc=0x{current_pc & MASK64:016x} stall={stall} "
        f"redirect_valid={redirect_valid} redirect_pc=0x{redirect_pc & MASK64:016x} "
        f"expected=0x{expected:016x} got=0x{got:016x}"
    )


@cocotb.test()
async def test_pc_select_directed(dut):
    vectors = [
        ("SEQ_FROM_ZERO", 0x0000_0000_0000_0000, 0, 0, 0x0),
        ("SEQ_FROM_NONZERO", 0x0000_0000_0000_0100, 0, 0, 0x0),
        ("STALL_HOLD", 0x0000_0000_0000_0200, 1, 0, 0x0),
        ("REDIRECT", 0x0000_0000_0000_0300, 0, 1, 0x0000_0000_0000_4000),
        ("REDIRECT_OVER_STALL", 0x0000_0000_0000_0500, 1, 1, 0x0000_0000_0000_8000),
        (
            "WRAP_AROUND",
            0xFFFF_FFFF_FFFF_FFFC,
            0,
            0,
            0x0000_0000_0000_0000,
        ),
    ]

    for name, current_pc, stall, redirect_valid, redirect_pc in vectors:
        await check_case(dut, current_pc, stall, redirect_valid, redirect_pc, name)


@cocotb.test()
async def test_pc_select_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        current_pc = random.getrandbits(64)
        stall = random.getrandbits(1)
        redirect_valid = random.getrandbits(1)
        redirect_pc = random.getrandbits(64)
        await check_case(
            dut, current_pc, stall, redirect_valid, redirect_pc, f"RAND_{idx}"
        )
