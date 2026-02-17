import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1
NOP_INSTR = 0x0000_0013


def get_u64(signal) -> int:
    return int(signal.value) & MASK64


def get_u32(signal) -> int:
    return int(signal.value) & 0xFFFF_FFFF


def model_next_pc(
    current_pc: int,
    stall: int,
    imem_ready: int,
    redirect_valid: int,
    redirect_pc: int,
) -> int:
    if redirect_valid:
        return redirect_pc & MASK64
    if stall or not imem_ready:
        return current_pc & MASK64
    return (current_pc + 4) & MASK64


def expected_fetch_outputs(
    current_pc: int,
    stall: int,
    flush: int,
    imem_ready: int,
    imem_rdata: int,
) -> tuple[int, int, int, int]:
    fetch_req = 1 if (not stall) else 0
    imem_req = fetch_req
    imem_addr = current_pc & MASK64
    instr = NOP_INSTR if flush else (imem_rdata & 0xFFFF_FFFF)
    instr_valid = 0 if flush else (fetch_req and imem_ready)
    return imem_req, imem_addr, instr, instr_valid


async def reset_dut(dut, cycles: int = 5) -> None:
    dut.rst.value = 1
    dut.stall.value = 0
    dut.flush.value = 0
    dut.redirect_valid.value = 0
    dut.redirect_pc.value = 0
    dut.imem_ready.value = 1
    dut.imem_rdata.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await Timer(1, unit="ns")
    assert get_u64(dut.pc) == 0, "PC must start at reset vector"


def drive_inputs(
    dut,
    stall: int,
    flush: int,
    redirect_valid: int,
    redirect_pc: int,
    imem_ready: int,
    imem_rdata: int,
) -> None:
    dut.stall.value = stall
    dut.flush.value = flush
    dut.redirect_valid.value = redirect_valid
    dut.redirect_pc.value = redirect_pc & MASK64
    dut.imem_ready.value = imem_ready
    dut.imem_rdata.value = imem_rdata & 0xFFFF_FFFF


def check_outputs(
    dut,
    model_pc: int,
    stall: int,
    flush: int,
    imem_ready: int,
    imem_rdata: int,
    name: str,
) -> None:
    got_pc = get_u64(dut.pc)
    got_req = int(dut.imem_req.value)
    got_addr = get_u64(dut.imem_addr)
    got_instr = get_u32(dut.instr)
    got_valid = int(dut.instr_valid.value)

    exp_req, exp_addr, exp_instr, exp_valid = expected_fetch_outputs(
        model_pc, stall, flush, imem_ready, imem_rdata
    )

    assert got_pc == (model_pc & MASK64), f"{name}: PC mismatch"
    assert got_req == exp_req, f"{name}: imem_req mismatch"
    assert got_addr == exp_addr, f"{name}: imem_addr mismatch"
    assert got_instr == exp_instr, f"{name}: instr mismatch"
    assert got_valid == exp_valid, f"{name}: instr_valid mismatch"


@cocotb.test()
async def test_if_stage_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    model_pc = 0

    # Reset vector and sequential fetch behavior.
    for step in range(4):
        rdata = 0x1000_0000 + step
        drive_inputs(
            dut,
            stall=0,
            flush=0,
            redirect_valid=0,
            redirect_pc=0,
            imem_ready=1,
            imem_rdata=rdata,
        )
        await Timer(1, unit="ns")
        check_outputs(dut, model_pc, 0, 0, 1, rdata, f"SEQ_{step}")

        await RisingEdge(dut.clk)
        model_pc = model_next_pc(model_pc, 0, 1, 0, 0)

    # Memory backpressure holds PC and suppresses valid fetch output.
    drive_inputs(
        dut,
        stall=0,
        flush=0,
        redirect_valid=0,
        redirect_pc=0,
        imem_ready=0,
        imem_rdata=0xAAAA_AAAA,
    )
    await Timer(1, unit="ns")
    check_outputs(dut, model_pc, 0, 0, 0, 0xAAAA_AAAA, "BACKPRESSURE")

    await RisingEdge(dut.clk)
    model_pc = model_next_pc(model_pc, 0, 0, 0, 0)

    # Flush discards the current fetch.
    drive_inputs(
        dut,
        stall=0,
        flush=1,
        redirect_valid=0,
        redirect_pc=0,
        imem_ready=1,
        imem_rdata=0xBBBB_BBBB,
    )
    await Timer(1, unit="ns")
    check_outputs(dut, model_pc, 0, 1, 1, 0xBBBB_BBBB, "FLUSH")

    await RisingEdge(dut.clk)
    model_pc = model_next_pc(model_pc, 0, 1, 0, 0)

    # Redirect updates PC on next edge.
    redirect_pc = 0x0000_0000_0000_2000
    drive_inputs(
        dut,
        stall=0,
        flush=1,
        redirect_valid=1,
        redirect_pc=redirect_pc,
        imem_ready=1,
        imem_rdata=0xCCCC_CCCC,
    )
    await Timer(1, unit="ns")
    check_outputs(dut, model_pc, 0, 1, 1, 0xCCCC_CCCC, "REDIRECT")

    await RisingEdge(dut.clk)
    model_pc = model_next_pc(model_pc, 0, 1, 1, redirect_pc)
    assert model_pc == redirect_pc

    # Redirect must override stall and memory-not-ready hold behavior.
    redirect_pc_2 = 0x0000_0000_0000_3000
    drive_inputs(
        dut,
        stall=1,
        flush=1,
        redirect_valid=1,
        redirect_pc=redirect_pc_2,
        imem_ready=0,
        imem_rdata=0xDDDD_DDDD,
    )
    await Timer(1, unit="ns")
    check_outputs(dut, model_pc, 1, 1, 0, 0xDDDD_DDDD, "REDIRECT_OVER_STALL")

    await RisingEdge(dut.clk)
    model_pc = model_next_pc(model_pc, 1, 0, 1, redirect_pc_2)
    assert model_pc == redirect_pc_2


@cocotb.test()
async def test_if_stage_randomized(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    random.seed(64)

    model_pc = 0

    for idx in range(3000):
        stall = random.getrandbits(1)
        flush = random.getrandbits(1)
        redirect_valid = random.getrandbits(1)
        redirect_pc = random.getrandbits(64) & ~0x3
        imem_ready = random.getrandbits(1)
        imem_rdata = random.getrandbits(32)

        drive_inputs(
            dut,
            stall=stall,
            flush=flush,
            redirect_valid=redirect_valid,
            redirect_pc=redirect_pc,
            imem_ready=imem_ready,
            imem_rdata=imem_rdata,
        )

        await Timer(1, unit="ns")
        check_outputs(
            dut,
            model_pc,
            stall,
            flush,
            imem_ready,
            imem_rdata,
            f"RAND_{idx}",
        )

        await RisingEdge(dut.clk)
        model_pc = model_next_pc(
            model_pc,
            stall,
            imem_ready,
            redirect_valid,
            redirect_pc,
        )
