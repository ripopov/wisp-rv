import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

MASK32 = (1 << 32) - 1
MASK64 = (1 << 64) - 1

# Kept in sync with units/ram_model/Makefile -G overrides.
A_LATENCY = 2
B_LATENCY = 3


def merge_write_bytes(prior: int, wdata: int, be: int) -> int:
    merged = prior & MASK64
    for i in range(8):
        if (be >> i) & 1:
            byte = (wdata >> (8 * i)) & 0xFF
            merged &= ~(0xFF << (8 * i))
            merged |= byte << (8 * i)
    return merged & MASK64


async def wait_a_ready(dut, max_cycles: int = 128) -> tuple[int, int]:
    waited = 0
    for _ in range(max_cycles):
        await Timer(1, unit="ns")
        ready = int(dut.a_ready.value)
        rdata = int(dut.a_rdata.value) & MASK32
        if ready:
            await RisingEdge(dut.clk)
            return waited, rdata
        await RisingEdge(dut.clk)
        waited += 1
    raise AssertionError("Timed out waiting for a_ready")


async def wait_b_ready(dut, max_cycles: int = 128) -> tuple[int, int]:
    waited = 0
    for _ in range(max_cycles):
        await Timer(1, unit="ns")
        ready = int(dut.b_ready.value)
        rdata = int(dut.b_rdata.value) & MASK64
        if ready:
            await RisingEdge(dut.clk)
            return waited, rdata
        await RisingEdge(dut.clk)
        waited += 1
    raise AssertionError("Timed out waiting for b_ready")


def init_inputs(dut) -> None:
    dut.a_addr.value = 0
    dut.a_req.value = 0

    dut.b_addr.value = 0
    dut.b_req.value = 0
    dut.b_wr.value = 0
    dut.b_wdata.value = 0
    dut.b_be.value = 0

    dut.tb_wr_en.value = 0
    dut.tb_wr_addr.value = 0
    dut.tb_wr_data.value = 0
    dut.tb_wr_be.value = 0
    dut.tb_rd_addr.value = 0


def clear_memory(dut, words: int = 256) -> None:
    for idx in range(words):
        dut.mem[idx].value = 0


@cocotb.test()
async def test_ram_model_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    init_inputs(dut)
    clear_memory(dut)
    await RisingEdge(dut.clk)

    target_addr = 0x18
    full_write = 0x1122_3344_5566_7788

    # Full-width write.
    dut.b_addr.value = target_addr
    dut.b_wdata.value = full_write
    dut.b_be.value = 0xFF
    dut.b_wr.value = 1
    dut.b_req.value = 1
    waited, _ = await wait_b_ready(dut)
    assert waited == B_LATENCY
    dut.b_req.value = 0
    dut.b_wr.value = 0

    # Full-width readback.
    dut.b_addr.value = target_addr
    dut.b_be.value = 0
    dut.b_wr.value = 0
    dut.b_req.value = 1
    waited, got = await wait_b_ready(dut)
    assert waited == B_LATENCY
    assert got == full_write
    dut.b_req.value = 0

    # Partial-byte write, then readback.
    partial_write = 0xAABB_CCDD_EEFF_0011
    partial_be = 0x0F
    expected = merge_write_bytes(full_write, partial_write, partial_be)

    dut.b_addr.value = target_addr
    dut.b_wdata.value = partial_write
    dut.b_be.value = partial_be
    dut.b_wr.value = 1
    dut.b_req.value = 1
    waited, _ = await wait_b_ready(dut)
    assert waited == B_LATENCY
    dut.b_req.value = 0
    dut.b_wr.value = 0

    dut.b_addr.value = target_addr
    dut.b_req.value = 1
    waited, got = await wait_b_ready(dut)
    assert waited == B_LATENCY
    assert got == expected
    dut.b_req.value = 0

    # Port A lower/upper 32-bit fetches.
    dut.a_addr.value = target_addr
    dut.a_req.value = 1
    waited, got_low = await wait_a_ready(dut)
    assert waited == A_LATENCY
    assert got_low == (expected & MASK32)
    dut.a_req.value = 0

    dut.a_addr.value = target_addr + 4
    dut.a_req.value = 1
    waited, got_high = await wait_a_ready(dut)
    assert waited == A_LATENCY
    assert got_high == ((expected >> 32) & MASK32)
    dut.a_req.value = 0


@cocotb.test()
async def test_ram_model_randomized(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    init_inputs(dut)
    clear_memory(dut)
    await RisingEdge(dut.clk)

    random.seed(64)
    model: dict[int, int] = {}

    for _ in range(600):
        op = random.randrange(3)
        word_idx = random.randrange(0, 128)
        base_addr = word_idx << 3

        dut.a_req.value = 0
        dut.b_req.value = 0
        dut.b_wr.value = 0
        dut.b_be.value = 0
        dut.b_wdata.value = 0
        await RisingEdge(dut.clk)

        if op == 0:
            wdata = random.getrandbits(64)
            be = random.getrandbits(8)

            dut.b_addr.value = base_addr
            dut.b_wdata.value = wdata
            dut.b_be.value = be
            dut.b_wr.value = 1
            dut.b_req.value = 1

            waited, _ = await wait_b_ready(dut)
            assert waited == B_LATENCY

            prior = model.get(word_idx, 0)
            model[word_idx] = merge_write_bytes(prior, wdata, be)

            dut.b_req.value = 0
            dut.b_wr.value = 0

        elif op == 1:
            dut.b_addr.value = base_addr
            dut.b_wr.value = 0
            dut.b_req.value = 1

            waited, got = await wait_b_ready(dut)
            assert waited == B_LATENCY
            assert got == model.get(word_idx, 0)

            dut.b_req.value = 0

        else:
            lane = random.randrange(2)
            addr = base_addr + (lane * 4)
            expected_word = model.get(word_idx, 0)
            expected = (expected_word >> (lane * 32)) & MASK32

            dut.a_addr.value = addr
            dut.a_req.value = 1

            waited, got = await wait_a_ready(dut)
            assert waited == A_LATENCY
            assert got == expected

            dut.a_req.value = 0
