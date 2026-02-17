import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1


def to_u64(value: int) -> int:
    return value & MASK64


def get_u64(signal) -> int:
    return int(signal.value) & MASK64


async def reset_dut(dut, cycles: int = 5) -> None:
    dut.rst.value = 1
    dut.wr_en.value = 0
    dut.wr_addr.value = 0
    dut.wr_data.value = 0
    dut.rs1_addr.value = 0
    dut.rs2_addr.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_regfile_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    expected = [0] * 32

    # Write every architectural register except x0 and verify same-cycle bypass.
    for idx in range(1, 32):
        value = to_u64((idx * 0x1111_1111_1111_1111) ^ 0x0123_4567_89AB_CDEF)

        dut.wr_en.value = 1
        dut.wr_addr.value = idx
        dut.wr_data.value = value
        dut.rs1_addr.value = idx
        dut.rs2_addr.value = 0
        await Timer(1, unit="ns")

        assert get_u64(dut.rs1_data) == value, f"Bypass mismatch for x{idx}"
        assert get_u64(dut.rs2_data) == 0, "x0 must read as zero"

        await RisingEdge(dut.clk)
        expected[idx] = value

    # Readback after writes.
    dut.wr_en.value = 0
    for idx in range(1, 32):
        dut.rs1_addr.value = idx
        dut.rs2_addr.value = 0
        await Timer(1, unit="ns")
        assert get_u64(dut.rs1_data) == expected[idx], f"Readback mismatch for x{idx}"
        assert get_u64(dut.rs2_data) == 0

    # Simultaneous read/write of different registers should be independent.
    src = 7
    dst = 13
    new_dst_value = to_u64(0xDEAD_BEEF_CAFE_1234)
    dut.wr_en.value = 1
    dut.wr_addr.value = dst
    dut.wr_data.value = new_dst_value
    dut.rs1_addr.value = src
    dut.rs2_addr.value = dst
    await Timer(1, unit="ns")

    assert get_u64(dut.rs1_data) == expected[src], "Read of unaffected register changed"
    assert get_u64(dut.rs2_data) == new_dst_value, "Destination bypass value mismatch"

    await RisingEdge(dut.clk)
    expected[dst] = new_dst_value

    # x0 writes must be ignored and bypass must not leak into x0 reads.
    dut.wr_en.value = 1
    dut.wr_addr.value = 0
    dut.wr_data.value = to_u64(0xFFFF_FFFF_FFFF_FFFF)
    dut.rs1_addr.value = 0
    dut.rs2_addr.value = src
    await Timer(1, unit="ns")

    assert get_u64(dut.rs1_data) == 0, "x0 bypass leaked write data"
    assert get_u64(dut.rs2_data) == expected[src], "Non-x0 read changed during x0 write"

    await RisingEdge(dut.clk)
    dut.wr_en.value = 0
    dut.rs1_addr.value = 0
    dut.rs2_addr.value = 0
    await Timer(1, unit="ns")
    assert get_u64(dut.rs1_data) == 0, "x0 changed after write attempt"
    assert get_u64(dut.rs2_data) == 0, "x0 changed after write attempt"


@cocotb.test()
async def test_regfile_randomized(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    random.seed(64)

    model = [0] * 32

    for _ in range(2000):
        wr_en = random.getrandbits(1)
        wr_addr = random.randrange(32)
        wr_data = random.getrandbits(64)
        rs1_addr = random.randrange(32)
        rs2_addr = random.randrange(32)

        dut.wr_en.value = wr_en
        dut.wr_addr.value = wr_addr
        dut.wr_data.value = wr_data
        dut.rs1_addr.value = rs1_addr
        dut.rs2_addr.value = rs2_addr

        def expected_read(addr: int) -> int:
            if addr == 0:
                return 0
            if wr_en and wr_addr != 0 and wr_addr == addr:
                return to_u64(wr_data)
            return model[addr]

        await Timer(1, unit="ns")

        assert get_u64(dut.rs1_data) == expected_read(rs1_addr)
        assert get_u64(dut.rs2_data) == expected_read(rs2_addr)

        await RisingEdge(dut.clk)
        if wr_en and wr_addr != 0:
            model[wr_addr] = to_u64(wr_data)
