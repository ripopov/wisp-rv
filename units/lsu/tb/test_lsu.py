import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1

F3_LB = 0b000
F3_LH = 0b001
F3_LW = 0b010
F3_LD = 0b011
F3_LBU = 0b100
F3_LHU = 0b101
F3_LWU = 0b110

F3_SB = 0b000
F3_SH = 0b001
F3_SW = 0b010
F3_SD = 0b011

VALID_LOAD_F3 = {F3_LB, F3_LH, F3_LW, F3_LD, F3_LBU, F3_LHU, F3_LWU}
VALID_STORE_F3 = {F3_SB, F3_SH, F3_SW, F3_SD}


def sign_extend(value: int, bits: int) -> int:
    value &= (1 << bits) - 1
    sign_bit = 1 << (bits - 1)
    if value & sign_bit:
        value -= 1 << bits
    return value & MASK64


def model_load_align(mem_rdata: int, addr_lsb: int, funct3: int) -> int:
    shifted = (mem_rdata & MASK64) >> ((addr_lsb & 0x7) * 8)

    if funct3 == F3_LB:
        return sign_extend(shifted, 8)
    if funct3 == F3_LH:
        return sign_extend(shifted, 16)
    if funct3 == F3_LW:
        return sign_extend(shifted, 32)
    if funct3 == F3_LD:
        return shifted & MASK64
    if funct3 == F3_LBU:
        return shifted & 0xFF
    if funct3 == F3_LHU:
        return shifted & 0xFFFF
    if funct3 == F3_LWU:
        return shifted & 0xFFFF_FFFF
    return 0


def model_store_align(
    store_data_in: int, addr_lsb: int, funct3: int
) -> tuple[int, int]:
    shift = (addr_lsb & 0x7) * 8

    if funct3 == F3_SB:
        return ((store_data_in & 0xFF) << shift) & MASK64, (0x01 << addr_lsb) & 0xFF
    if funct3 == F3_SH:
        return ((store_data_in & 0xFFFF) << shift) & MASK64, (0x03 << addr_lsb) & 0xFF
    if funct3 == F3_SW:
        return ((store_data_in & 0xFFFF_FFFF) << shift) & MASK64, (
            0x0F << addr_lsb
        ) & 0xFF
    if funct3 == F3_SD:
        return store_data_in & MASK64, 0xFF
    return 0, 0


class LSUModelState:
    def __init__(self):
        self.pending_load = 0
        self.pending_addr_lsb = 0
        self.pending_funct3 = 0


def eval_model(
    state: LSUModelState,
    mem_read: int,
    mem_write: int,
    funct3: int,
    addr: int,
    store_data_in: int,
    dmem_ready: int,
    dmem_rdata: int,
) -> tuple[dict[str, int], LSUModelState]:
    is_load = 1 if (mem_read and not mem_write) else 0
    is_store = 1 if (mem_write and not mem_read) else 0
    access = 1 if (mem_read or mem_write) else 0

    valid_load_f3 = funct3 in VALID_LOAD_F3
    valid_store_f3 = funct3 in VALID_STORE_F3

    invalid_access = (
        (mem_read and mem_write)
        or (mem_read and not valid_load_f3)
        or (mem_write and not valid_store_f3)
    )

    is_half = funct3 in (F3_LH, F3_LHU, F3_SH)
    is_word = funct3 in (F3_LW, F3_LWU, F3_SW)
    is_dword = funct3 in (F3_LD, F3_SD)
    alignment_mismatch = (
        (is_half and (addr & 0x1) != 0)
        or (is_word and (addr & 0x3) != 0)
        or (is_dword and (addr & 0x7) != 0)
    )

    misaligned_access = 1 if (access and (invalid_access or alignment_mismatch)) else 0

    if state.pending_load:
        load_addr_lsb = state.pending_addr_lsb
        load_funct3 = state.pending_funct3
    else:
        load_addr_lsb = addr & 0x7
        load_funct3 = funct3 & 0x7

    store_data, byte_en = model_store_align(store_data_in, addr & 0x7, funct3)

    request_valid = (
        1 if (access and not misaligned_access and not state.pending_load) else 0
    )
    dmem_req = request_valid
    dmem_we = is_store
    dmem_addr = addr & MASK64
    dmem_wdata = store_data & MASK64
    dmem_byte_en = byte_en & 0xFF

    req_accepted = 1 if (dmem_req and dmem_ready) else 0
    resp_valid = 1 if state.pending_load else 0
    load_data = model_load_align(dmem_rdata, load_addr_lsb, load_funct3)
    load_valid = 1 if (resp_valid and state.pending_load) else 0

    mem_stall = 0
    if state.pending_load:
        mem_stall = 0 if load_valid else 1
    elif is_store and not misaligned_access:
        mem_stall = 0 if req_accepted else 1
    elif is_load and not misaligned_access:
        mem_stall = 0 if load_valid else 1

    next_state = LSUModelState()
    next_state.pending_load = state.pending_load
    next_state.pending_addr_lsb = state.pending_addr_lsb
    next_state.pending_funct3 = state.pending_funct3

    if state.pending_load:
        next_state.pending_load = 0
    elif req_accepted and is_load:
        next_state.pending_load = 1
        next_state.pending_addr_lsb = addr & 0x7
        next_state.pending_funct3 = funct3 & 0x7

    outputs = {
        "load_data": load_data & MASK64,
        "load_valid": load_valid,
        "mem_stall": mem_stall,
        "misaligned_access": misaligned_access,
        "dmem_req": dmem_req,
        "dmem_we": dmem_we,
        "dmem_addr": dmem_addr,
        "dmem_wdata": dmem_wdata,
        "dmem_byte_en": dmem_byte_en,
    }

    return outputs, next_state


async def reset_dut(dut, cycles: int = 5) -> None:
    dut.rst.value = 1
    dut.mem_read.value = 0
    dut.mem_write.value = 0
    dut.funct3.value = 0
    dut.addr.value = 0
    dut.store_data_in.value = 0
    dut.dmem_ready.value = 0
    dut.dmem_rdata.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


def drive_inputs(
    dut,
    mem_read: int,
    mem_write: int,
    funct3: int,
    addr: int,
    store_data_in: int,
    dmem_ready: int,
    dmem_rdata: int,
) -> None:
    dut.mem_read.value = mem_read
    dut.mem_write.value = mem_write
    dut.funct3.value = funct3 & 0x7
    dut.addr.value = addr & MASK64
    dut.store_data_in.value = store_data_in & MASK64
    dut.dmem_ready.value = dmem_ready
    dut.dmem_rdata.value = dmem_rdata & MASK64


def check_outputs(dut, expected: dict[str, int], name: str) -> None:
    got = {
        "load_data": int(dut.load_data.value) & MASK64,
        "load_valid": int(dut.load_valid.value),
        "mem_stall": int(dut.mem_stall.value),
        "misaligned_access": int(dut.misaligned_access.value),
        "dmem_req": int(dut.dmem_req.value),
        "dmem_we": int(dut.dmem_we.value),
        "dmem_addr": int(dut.dmem_addr.value) & MASK64,
        "dmem_wdata": int(dut.dmem_wdata.value) & MASK64,
        "dmem_byte_en": int(dut.dmem_byte_en.value) & 0xFF,
    }

    for field, exp in expected.items():
        assert got[field] == exp, (
            f"{name}: {field} mismatch expected=0x{exp:x} got=0x{got[field]:x}"
        )


async def step_cycle(dut, state: LSUModelState, name: str, **inputs) -> LSUModelState:
    drive_inputs(dut, **inputs)
    await Timer(1, unit="ns")
    expected, next_state = eval_model(state, **inputs)
    check_outputs(dut, expected, name)
    await RisingEdge(dut.clk)
    return next_state


@cocotb.test()
async def test_lsu_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    state = LSUModelState()

    state = await step_cycle(
        dut,
        state,
        "MISALIGNED_LD",
        mem_read=1,
        mem_write=0,
        funct3=F3_LD,
        addr=0x0000_0000_0000_0004,
        store_data_in=0,
        dmem_ready=1,
        dmem_rdata=0x0123_4567_89AB_CDEF,
    )

    state = await step_cycle(
        dut,
        state,
        "STORE_ACCEPTED",
        mem_read=0,
        mem_write=1,
        funct3=F3_SH,
        addr=0x0000_0000_0000_0002,
        store_data_in=0x0000_0000_0000_BEEF,
        dmem_ready=1,
        dmem_rdata=0,
    )

    state = await step_cycle(
        dut,
        state,
        "STORE_BACKPRESSURE",
        mem_read=0,
        mem_write=1,
        funct3=F3_SW,
        addr=0x0000_0000_0000_0004,
        store_data_in=0x1122_3344_5566_7788,
        dmem_ready=0,
        dmem_rdata=0,
    )

    state = await step_cycle(
        dut,
        state,
        "LOAD_REQ_CYCLE",
        mem_read=1,
        mem_write=0,
        funct3=F3_LW,
        addr=0x0000_0000_0000_0010,
        store_data_in=0,
        dmem_ready=1,
        dmem_rdata=0x0000_0000_8000_0001,
    )

    state = await step_cycle(
        dut,
        state,
        "LOAD_RESP_CYCLE",
        mem_read=1,
        mem_write=0,
        funct3=F3_LW,
        addr=0x0000_0000_0000_0010,
        store_data_in=0,
        dmem_ready=1,
        dmem_rdata=0x0000_0000_8000_0001,
    )

    # Verify response uses captured addr/funct3, not current-cycle values.
    state = await step_cycle(
        dut,
        state,
        "LBU_REQ_CAPTURE",
        mem_read=1,
        mem_write=0,
        funct3=F3_LBU,
        addr=0x0000_0000_0000_0003,
        store_data_in=0,
        dmem_ready=1,
        dmem_rdata=0,
    )

    state = await step_cycle(
        dut,
        state,
        "LBU_RESP_CAPTURED_FUNCT3",
        mem_read=1,
        mem_write=0,
        funct3=F3_LW,
        addr=0x0000_0000_0000_0000,
        store_data_in=0,
        dmem_ready=1,
        dmem_rdata=0x89AB_CDEF_0123_4567,
    )


@cocotb.test()
async def test_lsu_randomized(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    random.seed(64)

    state = LSUModelState()

    request = {
        "mem_read": 0,
        "mem_write": 0,
        "funct3": 0,
        "addr": 0,
        "store_data_in": 0,
    }

    hold_request = False

    for idx in range(3000):
        if not hold_request:
            op = random.randrange(4)
            if op == 0:
                request["mem_read"] = 0
                request["mem_write"] = 0
                request["funct3"] = random.getrandbits(3)
            elif op == 1:
                request["mem_read"] = 1
                request["mem_write"] = 0
                request["funct3"] = random.getrandbits(3)
            elif op == 2:
                request["mem_read"] = 0
                request["mem_write"] = 1
                request["funct3"] = random.getrandbits(3)
            else:
                request["mem_read"] = 1
                request["mem_write"] = 1
                request["funct3"] = random.getrandbits(3)

            request["addr"] = random.getrandbits(64)
            request["store_data_in"] = random.getrandbits(64)

        dmem_ready = random.getrandbits(1)
        dmem_rdata = random.getrandbits(64)

        inputs = {
            **request,
            "dmem_ready": dmem_ready,
            "dmem_rdata": dmem_rdata,
        }

        drive_inputs(dut, **inputs)
        await Timer(1, unit="ns")

        expected, next_state = eval_model(state, **inputs)
        check_outputs(dut, expected, f"RAND_{idx}")

        hold_request = expected["mem_stall"] == 1

        await RisingEdge(dut.clk)
        state = next_state
