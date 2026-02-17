import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1
DIV_LATENCY = 8


def u64(value: int) -> int:
    return value & MASK64


class CtrlModel:
    def __init__(self) -> None:
        self.busy = 0
        self.count = 0
        self.div_result_latched = 0

    def comb(
        self,
        *,
        flush: int,
        ex_valid: int,
        ex_is_mul: int,
        ex_is_div: int,
        mul_result: int,
        div_result: int,
    ) -> dict[str, int]:
        start_div = (
            1 if (ex_valid and ex_is_div and (not self.busy) and (not flush)) else 0
        )
        div_done = 1 if (self.busy and self.count == DIV_LATENCY - 1) else 0

        ex_busy_stall = 1 if ((start_div or self.busy) and (not div_done)) else 0

        m_result_valid = 0
        m_result = 0
        if self.busy:
            if div_done:
                m_result_valid = 1
                m_result = u64(self.div_result_latched)
        elif ex_valid and ex_is_mul:
            m_result_valid = 1
            m_result = u64(mul_result)

        return {
            "ex_busy_stall": ex_busy_stall,
            "m_result_valid": m_result_valid,
            "m_result": m_result,
            "start_div": start_div,
            "div_done": div_done,
        }

    def tick(
        self,
        *,
        rst: int,
        flush: int,
        start_div: int,
        div_done: int,
        div_result: int,
    ) -> None:
        if rst or flush:
            self.busy = 0
            self.count = 0
            self.div_result_latched = 0
        elif start_div:
            self.busy = 1
            self.count = 0
            self.div_result_latched = u64(div_result)
        elif self.busy:
            if div_done:
                self.busy = 0
                self.count = 0
            else:
                self.count += 1


async def reset_dut(dut, cycles: int = 3) -> None:
    dut.rst.value = 1
    dut.flush.value = 0
    dut.ex_valid.value = 0
    dut.ex_is_mul.value = 0
    dut.ex_is_div.value = 0
    dut.mul_result.value = 0
    dut.div_result.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_m_ext_ctrl_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Non-M op: no stall, no result.
    dut.flush.value = 0
    dut.ex_valid.value = 1
    dut.ex_is_mul.value = 0
    dut.ex_is_div.value = 0
    dut.mul_result.value = 0x11
    dut.div_result.value = 0x22
    await Timer(1, unit="ns")
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 0

    # MUL: immediate result, no stall.
    dut.ex_is_mul.value = 1
    dut.ex_is_div.value = 0
    dut.mul_result.value = 0x1234_5678_9ABC_DEF0
    await Timer(1, unit="ns")
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 1
    assert int(dut.m_result.value) & MASK64 == 0x1234_5678_9ABC_DEF0

    # DIV: stall for DIV_LATENCY cycles, then emit one result pulse.
    dut.ex_is_mul.value = 0
    dut.ex_is_div.value = 1
    dut.div_result.value = 0x0BAD_F00D_DEAD_BEEF

    await Timer(1, unit="ns")
    assert int(dut.ex_busy_stall.value) == 1
    assert int(dut.m_result_valid.value) == 0

    for _ in range(DIV_LATENCY - 1):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        assert int(dut.ex_busy_stall.value) == 1
        assert int(dut.m_result_valid.value) == 0

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 1
    assert int(dut.m_result.value) & MASK64 == 0x0BAD_F00D_DEAD_BEEF

    dut.ex_valid.value = 0
    dut.ex_is_div.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 0

    # Flush cancels in-flight divide.
    dut.ex_valid.value = 1
    dut.ex_is_mul.value = 0
    dut.ex_is_div.value = 1
    dut.div_result.value = 0x0123_4567_89AB_CDEF
    await Timer(1, unit="ns")
    assert int(dut.ex_busy_stall.value) == 1

    await RisingEdge(dut.clk)
    dut.flush.value = 1
    await RisingEdge(dut.clk)
    dut.ex_valid.value = 0
    dut.ex_is_div.value = 0
    dut.flush.value = 0
    await Timer(1, unit="ns")
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 0


@cocotb.test()
async def test_m_ext_ctrl_randomized(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    random.seed(64)
    model = CtrlModel()

    for idx in range(5000):
        rst = 0
        flush = random.getrandbits(1)
        ex_valid = random.getrandbits(1)

        sel = random.getrandbits(2)
        ex_is_mul = 1 if (sel == 1 and ex_valid) else 0
        ex_is_div = 1 if (sel == 2 and ex_valid) else 0

        mul_result = random.getrandbits(64)
        div_result = random.getrandbits(64)

        dut.rst.value = rst
        dut.flush.value = flush
        dut.ex_valid.value = ex_valid
        dut.ex_is_mul.value = ex_is_mul
        dut.ex_is_div.value = ex_is_div
        dut.mul_result.value = mul_result
        dut.div_result.value = div_result

        await Timer(1, unit="ns")

        exp = model.comb(
            flush=flush,
            ex_valid=ex_valid,
            ex_is_mul=ex_is_mul,
            ex_is_div=ex_is_div,
            mul_result=mul_result,
            div_result=div_result,
        )

        got_ex_busy_stall = int(dut.ex_busy_stall.value)
        got_m_result_valid = int(dut.m_result_valid.value)
        got_m_result = int(dut.m_result.value) & MASK64

        assert got_ex_busy_stall == exp["ex_busy_stall"], (
            f"RAND_{idx}: ex_busy_stall expected {exp['ex_busy_stall']} got {got_ex_busy_stall}"
        )
        assert got_m_result_valid == exp["m_result_valid"], (
            f"RAND_{idx}: m_result_valid expected {exp['m_result_valid']} got {got_m_result_valid}"
        )
        assert got_m_result == exp["m_result"], (
            f"RAND_{idx}: m_result expected 0x{exp['m_result']:016x} got 0x{got_m_result:016x}"
        )

        await RisingEdge(dut.clk)
        model.tick(
            rst=rst,
            flush=flush,
            start_div=exp["start_div"],
            div_done=exp["div_done"],
            div_result=div_result,
        )
