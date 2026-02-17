import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1


def model_jump(
    pc: int, rs1_data: int, imm: int, jump: int, is_jalr: int
) -> tuple[int, int, int]:
    link_addr = (pc + 4) & MASK64
    if is_jalr:
        jump_target = ((rs1_data + imm) & MASK64) & ~0x1
    else:
        jump_target = (pc + imm) & MASK64
    jump_taken = 1 if jump else 0
    return jump_taken, jump_target, link_addr


async def check_case(
    dut,
    pc: int,
    rs1_data: int,
    imm: int,
    jump: int,
    is_jalr: int,
    name: str,
) -> None:
    dut.pc.value = pc & MASK64
    dut.rs1_data.value = rs1_data & MASK64
    dut.imm.value = imm & MASK64
    dut.jump.value = jump
    dut.is_jalr.value = is_jalr
    await Timer(1, unit="ns")

    exp_taken, exp_target, exp_link = model_jump(pc, rs1_data, imm, jump, is_jalr)
    got_taken = int(dut.jump_taken.value)
    got_target = int(dut.jump_target.value) & MASK64
    got_link = int(dut.link_addr.value) & MASK64

    assert got_taken == exp_taken, f"{name}: jump_taken mismatch"
    assert got_target == exp_target, f"{name}: jump_target mismatch"
    assert got_link == exp_link, f"{name}: link_addr mismatch"


@cocotb.test()
async def test_jump_unit_directed(dut):
    vectors = [
        (
            "JAL_BASIC",
            0x0000_0000_0000_1000,
            0,
            0x0000_0000_0000_0020,
            1,
            0,
        ),
        (
            "JALR_BASIC",
            0x0000_0000_0000_1000,
            0x0000_0000_0000_2003,
            0x0000_0000_0000_0008,
            1,
            1,
        ),
        (
            "JALR_ODD_SUM_MASK",
            0x0000_0000_0000_0000,
            0x0000_0000_0000_0001,
            0x0000_0000_0000_0002,
            1,
            1,
        ),
        (
            "NO_JUMP",
            0x0000_0000_0000_0040,
            0x0000_0000_0000_0100,
            0xFFFF_FFFF_FFFF_FFF0,
            0,
            0,
        ),
        (
            "WRAP_LINK",
            0xFFFF_FFFF_FFFF_FFFD,
            0,
            0,
            1,
            0,
        ),
    ]

    for name, pc, rs1_data, imm, jump, is_jalr in vectors:
        await check_case(dut, pc, rs1_data, imm, jump, is_jalr, name)


@cocotb.test()
async def test_jump_unit_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        pc = random.getrandbits(64)
        rs1_data = random.getrandbits(64)
        imm = random.getrandbits(64)
        jump = random.getrandbits(1)
        is_jalr = random.getrandbits(1)
        await check_case(dut, pc, rs1_data, imm, jump, is_jalr, f"RAND_{idx}")
