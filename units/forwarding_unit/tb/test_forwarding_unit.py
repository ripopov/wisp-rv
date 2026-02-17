import random

import cocotb
from cocotb.triggers import Timer

FWD_NONE = 0b00
FWD_EX_MEM = 0b01
FWD_MEM_WB = 0b10


def model_forward_sel(
    ex_mem_reg_write: int,
    ex_mem_rd: int,
    mem_wb_reg_write: int,
    mem_wb_rd: int,
    id_ex_src: int,
) -> int:
    if ex_mem_reg_write and ex_mem_rd != 0 and ex_mem_rd == id_ex_src:
        return FWD_EX_MEM
    if mem_wb_reg_write and mem_wb_rd != 0 and mem_wb_rd == id_ex_src:
        return FWD_MEM_WB
    return FWD_NONE


async def check_case(
    dut,
    *,
    ex_mem_reg_write: int,
    ex_mem_rd: int,
    mem_wb_reg_write: int,
    mem_wb_rd: int,
    id_ex_rs1: int,
    id_ex_rs2: int,
    name: str,
) -> None:
    dut.ex_mem_reg_write.value = ex_mem_reg_write
    dut.ex_mem_rd.value = ex_mem_rd
    dut.mem_wb_reg_write.value = mem_wb_reg_write
    dut.mem_wb_rd.value = mem_wb_rd
    dut.id_ex_rs1.value = id_ex_rs1
    dut.id_ex_rs2.value = id_ex_rs2
    await Timer(1, unit="ns")

    exp_a = model_forward_sel(
        ex_mem_reg_write,
        ex_mem_rd,
        mem_wb_reg_write,
        mem_wb_rd,
        id_ex_rs1,
    )
    exp_b = model_forward_sel(
        ex_mem_reg_write,
        ex_mem_rd,
        mem_wb_reg_write,
        mem_wb_rd,
        id_ex_rs2,
    )

    got_a = int(dut.forward_a_sel.value)
    got_b = int(dut.forward_b_sel.value)

    assert got_a == exp_a, f"{name}: forward_a_sel expected {exp_a} got {got_a}"
    assert got_b == exp_b, f"{name}: forward_b_sel expected {exp_b} got {got_b}"


@cocotb.test()
async def test_forwarding_unit_directed(dut):
    vectors = [
        {
            "name": "NO_MATCH",
            "ex_mem_reg_write": 0,
            "ex_mem_rd": 0,
            "mem_wb_reg_write": 0,
            "mem_wb_rd": 0,
            "id_ex_rs1": 1,
            "id_ex_rs2": 2,
        },
        {
            "name": "EX_MEM_RS1",
            "ex_mem_reg_write": 1,
            "ex_mem_rd": 3,
            "mem_wb_reg_write": 0,
            "mem_wb_rd": 0,
            "id_ex_rs1": 3,
            "id_ex_rs2": 4,
        },
        {
            "name": "MEM_WB_RS2",
            "ex_mem_reg_write": 0,
            "ex_mem_rd": 0,
            "mem_wb_reg_write": 1,
            "mem_wb_rd": 9,
            "id_ex_rs1": 1,
            "id_ex_rs2": 9,
        },
        {
            "name": "EX_MEM_PRIORITY",
            "ex_mem_reg_write": 1,
            "ex_mem_rd": 7,
            "mem_wb_reg_write": 1,
            "mem_wb_rd": 7,
            "id_ex_rs1": 7,
            "id_ex_rs2": 7,
        },
        {
            "name": "IGNORE_X0_EX_MEM",
            "ex_mem_reg_write": 1,
            "ex_mem_rd": 0,
            "mem_wb_reg_write": 1,
            "mem_wb_rd": 5,
            "id_ex_rs1": 0,
            "id_ex_rs2": 5,
        },
        {
            "name": "IGNORE_X0_MEM_WB",
            "ex_mem_reg_write": 0,
            "ex_mem_rd": 4,
            "mem_wb_reg_write": 1,
            "mem_wb_rd": 0,
            "id_ex_rs1": 6,
            "id_ex_rs2": 0,
        },
    ]

    for vec in vectors:
        await check_case(dut, **vec)


@cocotb.test()
async def test_forwarding_unit_randomized(dut):
    random.seed(64)

    for idx in range(20_000):
        await check_case(
            dut,
            ex_mem_reg_write=random.getrandbits(1),
            ex_mem_rd=random.getrandbits(5),
            mem_wb_reg_write=random.getrandbits(1),
            mem_wb_rd=random.getrandbits(5),
            id_ex_rs1=random.getrandbits(5),
            id_ex_rs2=random.getrandbits(5),
            name=f"RAND_{idx}",
        )
