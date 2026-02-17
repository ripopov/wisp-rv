import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer


FIELD_WIDTHS = {
    "if_id": {
        "pc": 64,
        "instr": 32,
        "valid": 1,
    },
    "id_ex": {
        "pc": 64,
        "rs1_data": 64,
        "rs2_data": 64,
        "imm": 64,
        "opcode": 7,
        "rd": 5,
        "rs1_addr": 5,
        "rs2_addr": 5,
        "funct3": 3,
        "funct7": 7,
        "alu_op": 4,
        "alu_src": 1,
        "mem_read": 1,
        "mem_write": 1,
        "reg_write": 1,
        "mem_to_reg": 1,
        "branch": 1,
        "jump": 1,
        "is_word_op": 1,
        "valid": 1,
    },
    "ex_mem": {
        "pc": 64,
        "alu_result": 64,
        "rs2_data": 64,
        "rd": 5,
        "funct3": 3,
        "mem_read": 1,
        "mem_write": 1,
        "reg_write": 1,
        "mem_to_reg": 1,
        "is_word_op": 1,
        "branch_taken": 1,
        "branch_target": 64,
        "valid": 1,
    },
    "mem_wb": {
        "alu_result": 64,
        "mem_data": 64,
        "rd": 5,
        "reg_write": 1,
        "mem_to_reg": 1,
        "valid": 1,
    },
}


def mask(width: int) -> int:
    return (1 << width) - 1


def zero_payload(prefix: str) -> dict[str, int]:
    return {field: 0 for field in FIELD_WIDTHS[prefix]}


def payload_from_seed(prefix: str, seed: int) -> dict[str, int]:
    payload = {}
    for idx, (field, width) in enumerate(FIELD_WIDTHS[prefix].items()):
        if width == 1:
            value = (seed + idx) & 1
        else:
            value = (seed * 0x1F12_3BB5 + idx * 0x9E37_79B9_7F4A_7C15) & mask(width)
        payload[field] = value
    return payload


def random_payload(prefix: str) -> dict[str, int]:
    return {
        field: random.getrandbits(width)
        for field, width in FIELD_WIDTHS[prefix].items()
    }


def set_stage_signals(
    dut, prefix: str, payload: dict[str, int], stall: int, flush: int
) -> None:
    getattr(dut, f"{prefix}_stall").value = stall
    getattr(dut, f"{prefix}_flush").value = flush
    for field, value in payload.items():
        getattr(dut, f"{prefix}_{field}_in").value = value


def read_stage_outputs(dut, prefix: str) -> dict[str, int]:
    return {
        field: int(getattr(dut, f"{prefix}_{field}_out").value)
        for field in FIELD_WIDTHS[prefix]
    }


def assert_stage_outputs(dut, prefix: str, expected: dict[str, int]) -> None:
    got = read_stage_outputs(dut, prefix)
    for field, width in FIELD_WIDTHS[prefix].items():
        exp = expected[field] & mask(width)
        got_val = got[field] & mask(width)
        assert got_val == exp, (
            f"{prefix}.{field} mismatch: expected 0x{exp:x}, got 0x{got_val:x}"
        )


def next_state(
    prev: dict[str, int],
    payload: dict[str, int],
    stall: int,
    flush: int,
) -> dict[str, int]:
    if flush:
        return {field: 0 for field in prev}
    if stall:
        return dict(prev)
    return dict(payload)


def drive_all_zero(dut) -> None:
    for prefix in FIELD_WIDTHS:
        set_stage_signals(dut, prefix, zero_payload(prefix), stall=0, flush=0)


async def reset_dut(dut, cycles: int = 5) -> None:
    drive_all_zero(dut)
    dut.rst.value = 1
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def exercise_stage_directed(dut, prefix: str, seed: int) -> None:
    payload_a = payload_from_seed(prefix, seed)
    payload_b = payload_from_seed(prefix, seed + 1)
    zeros = zero_payload(prefix)

    set_stage_signals(dut, prefix, payload_a, stall=0, flush=0)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert_stage_outputs(dut, prefix, payload_a)

    set_stage_signals(dut, prefix, payload_b, stall=1, flush=0)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert_stage_outputs(dut, prefix, payload_a)

    set_stage_signals(dut, prefix, payload_b, stall=0, flush=1)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert_stage_outputs(dut, prefix, zeros)

    set_stage_signals(dut, prefix, payload_a, stall=0, flush=0)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert_stage_outputs(dut, prefix, payload_a)

    set_stage_signals(dut, prefix, payload_b, stall=1, flush=1)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert_stage_outputs(dut, prefix, zeros)


@cocotb.test()
async def test_pipeline_regs_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    for prefix in FIELD_WIDTHS:
        assert_stage_outputs(dut, prefix, zero_payload(prefix))

    for idx, prefix in enumerate(FIELD_WIDTHS):
        await exercise_stage_directed(dut, prefix, seed=0x100 + idx * 0x10)


@cocotb.test()
async def test_pipeline_regs_randomized(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    random.seed(64)

    state = {prefix: zero_payload(prefix) for prefix in FIELD_WIDTHS}

    for _ in range(1500):
        cycle_inputs = {}
        cycle_stall = {}
        cycle_flush = {}

        for prefix in FIELD_WIDTHS:
            payload = random_payload(prefix)
            stall = random.getrandbits(1)
            flush = random.getrandbits(1)

            cycle_inputs[prefix] = payload
            cycle_stall[prefix] = stall
            cycle_flush[prefix] = flush
            set_stage_signals(dut, prefix, payload, stall=stall, flush=flush)

        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        for prefix in FIELD_WIDTHS:
            state[prefix] = next_state(
                prev=state[prefix],
                payload=cycle_inputs[prefix],
                stall=cycle_stall[prefix],
                flush=cycle_flush[prefix],
            )
            assert_stage_outputs(dut, prefix, state[prefix])
