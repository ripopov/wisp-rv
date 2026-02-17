import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1


def model_pipeline_ctrl(
    ex_redirect_valid: int,
    ex_redirect_pc: int,
    wb_redirect_valid: int,
    wb_redirect_pc: int,
    mem_stall: int,
    load_use_stall: int,
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
        "redirect_valid": 0,
        "redirect_pc": 0,
    }

    redirect_any = 1 if (wb_redirect_valid or ex_redirect_valid) else 0
    load_use_stall_effective = 1 if (load_use_stall and not redirect_any) else 0

    if wb_redirect_valid:
        out["redirect_valid"] = 1
        out["redirect_pc"] = wb_redirect_pc & MASK64
    elif ex_redirect_valid:
        out["redirect_valid"] = 1
        out["redirect_pc"] = ex_redirect_pc & MASK64

    if mem_stall:
        out["if_stage_stall"] = 1
        out["if_id_stall"] = 1
        out["id_ex_stall"] = 1
        out["ex_mem_stall"] = 1
    elif load_use_stall_effective:
        out["if_stage_stall"] = 1
        out["if_id_stall"] = 1
        out["id_ex_flush"] = 1

    if ex_redirect_valid:
        out["if_stage_flush"] = 1
        out["if_id_flush"] = 1
        out["id_ex_flush"] = 1

    if wb_redirect_valid:
        out["if_stage_flush"] = 1
        out["if_id_flush"] = 1
        out["id_ex_flush"] = 1
        out["ex_mem_flush"] = 1
        out["mem_wb_flush"] = 1

    return out


async def check_case(
    dut,
    ex_redirect_valid: int,
    ex_redirect_pc: int,
    wb_redirect_valid: int,
    wb_redirect_pc: int,
    mem_stall: int,
    load_use_stall: int,
    name: str,
) -> None:
    dut.ex_redirect_valid.value = ex_redirect_valid
    dut.ex_redirect_pc.value = ex_redirect_pc & MASK64
    dut.wb_redirect_valid.value = wb_redirect_valid
    dut.wb_redirect_pc.value = wb_redirect_pc & MASK64
    dut.mem_stall.value = mem_stall
    dut.load_use_stall.value = load_use_stall
    await Timer(1, unit="ns")

    expected = model_pipeline_ctrl(
        ex_redirect_valid,
        ex_redirect_pc,
        wb_redirect_valid,
        wb_redirect_pc,
        mem_stall,
        load_use_stall,
    )

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
        ("IDLE", 0, 0x0, 0, 0x0, 0, 0),
        ("LOAD_USE_ONLY", 0, 0x0, 0, 0x0, 0, 1),
        ("MEM_STALL_ONLY", 0, 0x1234, 0, 0x0, 1, 0),
        ("EX_REDIRECT_ONLY", 1, 0x1000, 0, 0x0, 0, 0),
        ("WB_REDIRECT_ONLY", 0, 0x0, 1, 0x9000, 0, 0),
        ("EX_REDIRECT_AND_MEM_STALL", 1, 0x2000, 0, 0x0, 1, 0),
        ("EX_REDIRECT_WINS_OVER_LOAD_USE", 1, 0x3000, 0, 0x0, 0, 1),
        ("WB_REDIRECT_WINS_OVER_EX", 1, 0x1111, 1, 0x2222, 0, 0),
        ("WB_REDIRECT_WINS_OVER_LOAD_USE", 0, 0x0, 1, 0x4444, 0, 1),
    ]

    for (
        name,
        ex_redirect_valid,
        ex_redirect_pc,
        wb_redirect_valid,
        wb_redirect_pc,
        mem_stall,
        load_use_stall,
    ) in vectors:
        await check_case(
            dut,
            ex_redirect_valid,
            ex_redirect_pc,
            wb_redirect_valid,
            wb_redirect_pc,
            mem_stall,
            load_use_stall,
            name,
        )


@cocotb.test()
async def test_pipeline_ctrl_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        ex_redirect_valid = random.getrandbits(1)
        ex_redirect_pc = random.getrandbits(64)
        wb_redirect_valid = random.getrandbits(1)
        wb_redirect_pc = random.getrandbits(64)
        mem_stall = random.getrandbits(1)
        load_use_stall = random.getrandbits(1)
        await check_case(
            dut,
            ex_redirect_valid,
            ex_redirect_pc,
            wb_redirect_valid,
            wb_redirect_pc,
            mem_stall,
            load_use_stall,
            f"RAND_{idx}",
        )
