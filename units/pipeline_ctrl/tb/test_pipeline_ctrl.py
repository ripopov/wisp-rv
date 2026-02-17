import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1


def model_pipeline_ctrl(
    ex_redirect_valid: int,
    ex_redirect_pc: int,
    mem_stall: int,
) -> dict[str, int]:
    out = {
        "if_stage_stall": 0,
        "if_stage_flush": 0,
        "if_id_stall": 0,
        "if_id_flush": 0,
        "id_ex_stall": 0,
        "id_ex_flush": 0,
        "ex_mem_stall": 0,
        "ex_mem_flush": 0,
        "mem_wb_stall": 0,
        "mem_wb_flush": 0,
        "redirect_valid": 1 if ex_redirect_valid else 0,
        "redirect_pc": ex_redirect_pc & MASK64,
    }

    if mem_stall:
        out["if_stage_stall"] = 1
        out["if_id_stall"] = 1
        out["id_ex_stall"] = 1
        out["ex_mem_stall"] = 1

    if ex_redirect_valid:
        out["if_stage_flush"] = 1
        out["if_id_flush"] = 1
        out["id_ex_flush"] = 1

    return out


async def check_case(
    dut,
    ex_redirect_valid: int,
    ex_redirect_pc: int,
    mem_stall: int,
    name: str,
) -> None:
    dut.ex_redirect_valid.value = ex_redirect_valid
    dut.ex_redirect_pc.value = ex_redirect_pc & MASK64
    dut.mem_stall.value = mem_stall
    await Timer(1, unit="ns")

    expected = model_pipeline_ctrl(ex_redirect_valid, ex_redirect_pc, mem_stall)

    for field in (
        "if_stage_stall",
        "if_stage_flush",
        "if_id_stall",
        "if_id_flush",
        "id_ex_stall",
        "id_ex_flush",
        "ex_mem_stall",
        "ex_mem_flush",
        "mem_wb_stall",
        "mem_wb_flush",
        "redirect_valid",
    ):
        got = int(getattr(dut, field).value)
        assert got == expected[field], (
            f"{name}: {field} expected {expected[field]} got {got}"
        )

    got_pc = int(dut.redirect_pc.value) & MASK64
    assert got_pc == expected["redirect_pc"], (
        f"{name}: redirect_pc expected 0x{expected['redirect_pc']:016x} got 0x{got_pc:016x}"
    )


@cocotb.test()
async def test_pipeline_ctrl_directed(dut):
    vectors = [
        ("IDLE", 0, 0x0, 0),
        ("MEM_STALL_ONLY", 0, 0x1234, 1),
        ("REDIRECT_ONLY", 1, 0x1000, 0),
        ("REDIRECT_AND_STALL", 1, 0x2000, 1),
    ]

    for name, ex_redirect_valid, ex_redirect_pc, mem_stall in vectors:
        await check_case(dut, ex_redirect_valid, ex_redirect_pc, mem_stall, name)


@cocotb.test()
async def test_pipeline_ctrl_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        ex_redirect_valid = random.getrandbits(1)
        ex_redirect_pc = random.getrandbits(64)
        mem_stall = random.getrandbits(1)
        await check_case(
            dut,
            ex_redirect_valid,
            ex_redirect_pc,
            mem_stall,
            f"RAND_{idx}",
        )
