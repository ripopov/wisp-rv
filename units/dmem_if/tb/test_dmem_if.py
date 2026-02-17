import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1


async def reset_dut(dut, cycles: int = 5) -> None:
    dut.rst.value = 1
    dut.req_valid.value = 0
    dut.req_we.value = 0
    dut.req_addr.value = 0
    dut.req_wdata.value = 0
    dut.req_byte_en.value = 0
    dut.mem_ready.value = 0
    dut.mem_rdata.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


def u64(signal) -> int:
    return int(signal.value) & MASK64


@cocotb.test()
async def test_dmem_if_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Read accepted: zero-latency responds immediately; one-cycle responds next cycle.
    dut.req_valid.value = 1
    dut.req_we.value = 0
    dut.req_addr.value = 0x40
    dut.req_wdata.value = 0xDEAD_BEEF_CAFE_F00D
    dut.req_byte_en.value = 0xFF
    dut.mem_ready.value = 1
    dut.mem_rdata.value = 0x0123_4567_89AB_CDEF
    await Timer(1, unit="ns")

    assert int(dut.z_dmem_req.value) == 1
    assert int(dut.z_req_accepted.value) == 1
    assert int(dut.z_resp_valid.value) == 1
    assert u64(dut.z_resp_rdata) == 0x0123_4567_89AB_CDEF

    assert int(dut.o_dmem_req.value) == 1
    assert int(dut.o_req_accepted.value) == 1
    assert int(dut.o_resp_valid.value) == 0

    await RisingEdge(dut.clk)
    dut.mem_rdata.value = 0x1111_2222_3333_4444
    await Timer(1, unit="ns")

    assert int(dut.o_dmem_req.value) == 0
    assert int(dut.o_req_accepted.value) == 0
    assert int(dut.o_resp_valid.value) == 1
    assert u64(dut.o_resp_rdata) == 0x1111_2222_3333_4444

    # Write accepted: no read response in either mode.
    await RisingEdge(dut.clk)
    dut.req_valid.value = 1
    dut.req_we.value = 1
    dut.req_addr.value = 0x88
    dut.req_wdata.value = 0xA5A5_A5A5_A5A5_A5A5
    dut.req_byte_en.value = 0x0F
    dut.mem_ready.value = 1
    dut.mem_rdata.value = 0x9999_9999_9999_9999
    await Timer(1, unit="ns")

    assert int(dut.z_req_accepted.value) == 1
    assert int(dut.z_resp_valid.value) == 0
    assert int(dut.o_req_accepted.value) == 1
    assert int(dut.o_resp_valid.value) == 0

    # Backpressure: ready low prevents acceptance.
    dut.mem_ready.value = 0
    await Timer(1, unit="ns")
    assert int(dut.z_req_accepted.value) == 0
    assert int(dut.o_req_accepted.value) == 0


@cocotb.test()
async def test_dmem_if_randomized(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    random.seed(64)

    pending_read = 0

    for _ in range(3000):
        req_valid = random.getrandbits(1)
        req_we = random.getrandbits(1)
        req_addr = random.getrandbits(64)
        req_wdata = random.getrandbits(64)
        req_byte_en = random.getrandbits(8)
        mem_ready = random.getrandbits(1)
        mem_rdata = random.getrandbits(64)

        dut.req_valid.value = req_valid
        dut.req_we.value = req_we
        dut.req_addr.value = req_addr
        dut.req_wdata.value = req_wdata
        dut.req_byte_en.value = req_byte_en
        dut.mem_ready.value = mem_ready
        dut.mem_rdata.value = mem_rdata
        await Timer(1, unit="ns")

        # Shared pass-through outputs.
        assert int(dut.z_dmem_we.value) == req_we
        assert int(dut.o_dmem_we.value) == req_we
        assert u64(dut.z_dmem_addr) == (req_addr & MASK64)
        assert u64(dut.o_dmem_addr) == (req_addr & MASK64)
        assert u64(dut.z_dmem_wdata) == (req_wdata & MASK64)
        assert u64(dut.o_dmem_wdata) == (req_wdata & MASK64)
        assert int(dut.z_dmem_byte_en.value) == (req_byte_en & 0xFF)
        assert int(dut.o_dmem_byte_en.value) == (req_byte_en & 0xFF)
        assert u64(dut.z_resp_rdata) == (mem_rdata & MASK64)
        assert u64(dut.o_resp_rdata) == (mem_rdata & MASK64)

        # Zero-latency model.
        z_dmem_req = req_valid
        z_req_accepted = req_valid & mem_ready
        z_resp_valid = req_valid & mem_ready & (0 if req_we else 1)
        assert int(dut.z_dmem_req.value) == z_dmem_req
        assert int(dut.z_req_accepted.value) == z_req_accepted
        assert int(dut.z_resp_valid.value) == z_resp_valid

        # One-cycle model.
        o_dmem_req = req_valid if pending_read == 0 else 0
        o_req_accepted = o_dmem_req & mem_ready
        o_resp_valid = pending_read
        assert int(dut.o_dmem_req.value) == o_dmem_req
        assert int(dut.o_req_accepted.value) == o_req_accepted
        assert int(dut.o_resp_valid.value) == o_resp_valid

        await RisingEdge(dut.clk)

        if pending_read:
            pending_read = 0
        elif o_req_accepted and (req_we == 0):
            pending_read = 1
