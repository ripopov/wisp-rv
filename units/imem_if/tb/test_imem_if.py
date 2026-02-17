import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1


async def reset_dut(dut, cycles: int = 5) -> None:
    dut.rst.value = 1
    dut.fetch_req.value = 0
    dut.fetch_addr.value = 0
    dut.mem_ready.value = 0
    dut.mem_rdata.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


def get_u64(signal) -> int:
    return int(signal.value) & MASK64


@cocotb.test()
async def test_imem_if_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Zero-latency: accepted request returns instruction in same cycle.
    dut.fetch_req.value = 1
    dut.fetch_addr.value = 0x40
    dut.mem_ready.value = 1
    dut.mem_rdata.value = 0x1234_5678
    await Timer(1, unit="ns")

    assert int(dut.z_imem_req.value) == 1
    assert get_u64(dut.z_imem_addr) == 0x40
    assert int(dut.z_instr_valid.value) == 1
    assert int(dut.z_instr.value) == 0x1234_5678

    # One-cycle mode: request first, response valid next cycle.
    assert int(dut.o_imem_req.value) == 1
    assert get_u64(dut.o_imem_addr) == 0x40
    assert int(dut.o_instr_valid.value) == 0

    await RisingEdge(dut.clk)
    dut.fetch_addr.value = 0x44
    dut.mem_rdata.value = 0x89AB_CDEF
    await Timer(1, unit="ns")

    assert int(dut.o_imem_req.value) == 0, (
        "One-cycle mode should block new request while pending"
    )
    assert int(dut.o_instr_valid.value) == 1
    assert int(dut.o_instr.value) == 0x89AB_CDEF

    await RisingEdge(dut.clk)
    dut.mem_ready.value = 0
    await Timer(1, unit="ns")

    # Ready low: requests can be presented but no zero-latency response is valid.
    assert int(dut.z_imem_req.value) == 1
    assert int(dut.z_instr_valid.value) == 0
    assert int(dut.o_imem_req.value) == 1
    assert int(dut.o_instr_valid.value) == 0


@cocotb.test()
async def test_imem_if_randomized_one_cycle_model(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    random.seed(64)

    pending = 0

    for _ in range(2000):
        fetch_req = random.getrandbits(1)
        fetch_addr = random.getrandbits(64)
        mem_ready = random.getrandbits(1)
        mem_rdata = random.getrandbits(32)

        dut.fetch_req.value = fetch_req
        dut.fetch_addr.value = fetch_addr
        dut.mem_ready.value = mem_ready
        dut.mem_rdata.value = mem_rdata
        await Timer(1, unit="ns")

        # Zero-latency checks.
        assert int(dut.z_imem_req.value) == fetch_req
        assert get_u64(dut.z_imem_addr) == (fetch_addr & MASK64)
        assert int(dut.z_instr_valid.value) == (fetch_req & mem_ready)
        assert int(dut.z_instr.value) == (mem_rdata & 0xFFFF_FFFF)

        # One-cycle checks based on local pending model.
        expected_o_req = fetch_req if pending == 0 else 0
        expected_o_valid = pending

        assert int(dut.o_imem_req.value) == expected_o_req
        assert get_u64(dut.o_imem_addr) == (fetch_addr & MASK64)
        assert int(dut.o_instr_valid.value) == expected_o_valid
        assert int(dut.o_instr.value) == (mem_rdata & 0xFFFF_FFFF)

        await RisingEdge(dut.clk)

        req_fire = 1 if (pending == 0 and fetch_req and mem_ready) else 0
        if pending:
            pending = 0
        elif req_fire:
            pending = 1
