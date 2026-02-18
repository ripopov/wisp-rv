import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1


def u64(value: int) -> int:
    return value & MASK64


def model_m_ext_ctrl(
    *,
    flush: int,
    ex_valid: int,
    ex_is_mul: int,
    ex_is_div: int,
    mul_result: int,
    div_busy: int,
    div_result_valid: int,
    div_result: int,
) -> tuple[int, int, int, int]:
    div_start = (
        1
        if (
            ex_valid
            and ex_is_div
            and (not flush)
            and (not div_busy)
            and (not div_result_valid)
        )
        else 0
    )

    ex_busy_stall = (
        1 if (ex_valid and ex_is_div and (not flush) and (not div_result_valid)) else 0
    )

    m_result_valid = 0
    m_result = 0
    if ex_valid and (not flush):
        if ex_is_mul:
            m_result_valid = 1
            m_result = u64(mul_result)
        elif ex_is_div and div_result_valid:
            m_result_valid = 1
            m_result = u64(div_result)

    return div_start, ex_busy_stall, m_result_valid, m_result


async def drive(
    dut,
    *,
    flush: int,
    ex_valid: int,
    ex_is_mul: int,
    ex_is_div: int,
    mul_result: int,
    div_busy: int,
    div_result_valid: int,
    div_result: int,
) -> None:
    dut.flush.value = flush
    dut.ex_valid.value = ex_valid
    dut.ex_is_mul.value = ex_is_mul
    dut.ex_is_div.value = ex_is_div
    dut.mul_result.value = u64(mul_result)
    dut.div_busy.value = div_busy
    dut.div_result_valid.value = div_result_valid
    dut.div_result.value = u64(div_result)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_m_ext_ctrl_directed(dut):
    await drive(
        dut,
        flush=0,
        ex_valid=1,
        ex_is_mul=0,
        ex_is_div=0,
        mul_result=0x11,
        div_busy=0,
        div_result_valid=0,
        div_result=0x22,
    )
    assert int(dut.div_start.value) == 0
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 0

    await drive(
        dut,
        flush=0,
        ex_valid=1,
        ex_is_mul=1,
        ex_is_div=0,
        mul_result=0x1234_5678_9ABC_DEF0,
        div_busy=0,
        div_result_valid=0,
        div_result=0,
    )
    assert int(dut.div_start.value) == 0
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 1
    assert (int(dut.m_result.value) & MASK64) == 0x1234_5678_9ABC_DEF0

    await drive(
        dut,
        flush=0,
        ex_valid=1,
        ex_is_mul=0,
        ex_is_div=1,
        mul_result=0,
        div_busy=0,
        div_result_valid=0,
        div_result=0x0BAD_F00D_DEAD_BEEF,
    )
    assert int(dut.div_start.value) == 1
    assert int(dut.ex_busy_stall.value) == 1
    assert int(dut.m_result_valid.value) == 0

    await drive(
        dut,
        flush=0,
        ex_valid=1,
        ex_is_mul=0,
        ex_is_div=1,
        mul_result=0,
        div_busy=1,
        div_result_valid=0,
        div_result=0x0BAD_F00D_DEAD_BEEF,
    )
    assert int(dut.div_start.value) == 0
    assert int(dut.ex_busy_stall.value) == 1
    assert int(dut.m_result_valid.value) == 0

    await drive(
        dut,
        flush=0,
        ex_valid=1,
        ex_is_mul=0,
        ex_is_div=1,
        mul_result=0,
        div_busy=0,
        div_result_valid=1,
        div_result=0x0BAD_F00D_DEAD_BEEF,
    )
    assert int(dut.div_start.value) == 0
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 1
    assert (int(dut.m_result.value) & MASK64) == 0x0BAD_F00D_DEAD_BEEF

    await drive(
        dut,
        flush=1,
        ex_valid=1,
        ex_is_mul=0,
        ex_is_div=1,
        mul_result=0xDEAD,
        div_busy=1,
        div_result_valid=1,
        div_result=0xBEEF,
    )
    assert int(dut.div_start.value) == 0
    assert int(dut.ex_busy_stall.value) == 0
    assert int(dut.m_result_valid.value) == 0


@cocotb.test()
async def test_m_ext_ctrl_randomized(dut):
    random.seed(64)

    for idx in range(10_000):
        flush = random.getrandbits(1)
        ex_valid = random.getrandbits(1)
        ex_is_mul = random.getrandbits(1)
        ex_is_div = random.getrandbits(1)
        mul_result = random.getrandbits(64)
        div_busy = random.getrandbits(1)
        div_result_valid = random.getrandbits(1)
        div_result = random.getrandbits(64)

        await drive(
            dut,
            flush=flush,
            ex_valid=ex_valid,
            ex_is_mul=ex_is_mul,
            ex_is_div=ex_is_div,
            mul_result=mul_result,
            div_busy=div_busy,
            div_result_valid=div_result_valid,
            div_result=div_result,
        )

        exp_div_start, exp_busy_stall, exp_result_valid, exp_result = model_m_ext_ctrl(
            flush=flush,
            ex_valid=ex_valid,
            ex_is_mul=ex_is_mul,
            ex_is_div=ex_is_div,
            mul_result=mul_result,
            div_busy=div_busy,
            div_result_valid=div_result_valid,
            div_result=div_result,
        )

        got_div_start = int(dut.div_start.value)
        got_busy_stall = int(dut.ex_busy_stall.value)
        got_result_valid = int(dut.m_result_valid.value)
        got_result = int(dut.m_result.value) & MASK64

        assert got_div_start == exp_div_start, (
            f"RAND_{idx}: div_start expected {exp_div_start} got {got_div_start}"
        )
        assert got_busy_stall == exp_busy_stall, (
            f"RAND_{idx}: ex_busy_stall expected {exp_busy_stall} got {got_busy_stall}"
        )
        assert got_result_valid == exp_result_valid, (
            f"RAND_{idx}: m_result_valid expected {exp_result_valid} got {got_result_valid}"
        )
        assert got_result == exp_result, (
            f"RAND_{idx}: m_result expected 0x{exp_result:016x} got 0x{got_result:016x}"
        )
