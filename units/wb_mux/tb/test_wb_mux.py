import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1


def model_wb_data(alu_result: int, mem_data: int, pc_plus4: int, wb_sel: int) -> int:
    if wb_sel == 0b00:
        return alu_result & MASK64
    if wb_sel == 0b01:
        return mem_data & MASK64
    if wb_sel == 0b10:
        return pc_plus4 & MASK64
    return alu_result & MASK64


async def check_case(
    dut,
    alu_result: int,
    mem_data: int,
    pc_plus4: int,
    wb_sel: int,
    name: str,
) -> None:
    dut.alu_result.value = alu_result & MASK64
    dut.mem_data.value = mem_data & MASK64
    dut.pc_plus4.value = pc_plus4 & MASK64
    dut.wb_sel.value = wb_sel & 0x3
    await Timer(1, unit="ns")

    expected = model_wb_data(alu_result, mem_data, pc_plus4, wb_sel)
    got = int(dut.wb_data.value) & MASK64
    assert got == expected, (
        f"{name}: wb_sel={wb_sel:02b} expected=0x{expected:016x} got=0x{got:016x}"
    )


@cocotb.test()
async def test_wb_mux_directed(dut):
    vectors = [
        ("ALU_PATH", 0x1111_2222_3333_4444, 0xAAAA_BBBB_CCCC_DDDD, 0x1234, 0b00),
        ("MEM_PATH", 0x1111_2222_3333_4444, 0xAAAA_BBBB_CCCC_DDDD, 0x1234, 0b01),
        ("PC4_PATH", 0x1111_2222_3333_4444, 0xAAAA_BBBB_CCCC_DDDD, 0x1234, 0b10),
        ("DEFAULT_PATH", 0x1111_2222_3333_4444, 0xAAAA_BBBB_CCCC_DDDD, 0x1234, 0b11),
    ]

    for name, alu_result, mem_data, pc_plus4, wb_sel in vectors:
        await check_case(dut, alu_result, mem_data, pc_plus4, wb_sel, name)


@cocotb.test()
async def test_wb_mux_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        alu_result = random.getrandbits(64)
        mem_data = random.getrandbits(64)
        pc_plus4 = random.getrandbits(64)
        wb_sel = random.getrandbits(2)
        await check_case(dut, alu_result, mem_data, pc_plus4, wb_sel, f"RAND_{idx}")
