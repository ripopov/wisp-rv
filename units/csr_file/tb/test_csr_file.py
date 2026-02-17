import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, Timer

MASK64 = (1 << 64) - 1

CSR_MSTATUS = 0x300
CSR_MISA = 0x301
CSR_MIE = 0x304
CSR_MTVEC = 0x305
CSR_MSCRATCH = 0x340
CSR_MEPC = 0x341
CSR_MCAUSE = 0x342
CSR_MTVAL = 0x343
CSR_MIP = 0x344
CSR_MVENDORID = 0xF11
CSR_MARCHID = 0xF12
CSR_MIMPID = 0xF13
CSR_MHARTID = 0xF14
CSR_MCYCLE = 0xB00
CSR_MINSTRET = 0xB02

CSR_CMD_NONE = 0
CSR_CMD_RW = 1
CSR_CMD_RS = 2
CSR_CMD_RC = 3
CSR_CMD_RWI = 4
CSR_CMD_RSI = 5
CSR_CMD_RCI = 6

MISA_RV64I = 0x8000_0000_0000_0100
MSTATUS_MASK = 0x1888


def csr_supported(addr: int) -> bool:
    return addr in {
        CSR_MSTATUS,
        CSR_MISA,
        CSR_MIE,
        CSR_MTVEC,
        CSR_MSCRATCH,
        CSR_MEPC,
        CSR_MCAUSE,
        CSR_MTVAL,
        CSR_MIP,
        CSR_MVENDORID,
        CSR_MARCHID,
        CSR_MIMPID,
        CSR_MHARTID,
        CSR_MCYCLE,
        CSR_MINSTRET,
    }


def csr_read_only(addr: int) -> bool:
    return addr in {
        CSR_MISA,
        CSR_MVENDORID,
        CSR_MARCHID,
        CSR_MIMPID,
        CSR_MHARTID,
    }


def csr_cmd_writes(cmd: int, wdata: int) -> bool:
    if cmd in (CSR_CMD_RW, CSR_CMD_RWI):
        return True
    if cmd in (CSR_CMD_RS, CSR_CMD_RSI, CSR_CMD_RC, CSR_CMD_RCI):
        return (wdata & MASK64) != 0
    return False


def apply_mask(addr: int, value: int) -> int:
    value &= MASK64
    if addr == CSR_MSTATUS:
        return value & MSTATUS_MASK
    if addr in (CSR_MTVEC, CSR_MEPC):
        return value & ~0x3
    return value


def read_model(state: dict[str, int], addr: int) -> int:
    if addr == CSR_MSTATUS:
        return state["mstatus"]
    if addr == CSR_MISA:
        return MISA_RV64I
    if addr == CSR_MIE:
        return state["mie"]
    if addr == CSR_MTVEC:
        return state["mtvec"]
    if addr == CSR_MSCRATCH:
        return state["mscratch"]
    if addr == CSR_MEPC:
        return state["mepc"]
    if addr == CSR_MCAUSE:
        return state["mcause"]
    if addr == CSR_MTVAL:
        return state["mtval"]
    if addr == CSR_MIP:
        return state["mip"]
    if addr in (CSR_MVENDORID, CSR_MARCHID, CSR_MIMPID, CSR_MHARTID):
        return 0
    if addr == CSR_MCYCLE:
        return state["mcycle"]
    if addr == CSR_MINSTRET:
        return state["minstret"]
    return 0


def update_state(state: dict[str, int], inputs: dict[str, int]) -> dict[str, int]:
    nxt = dict(state)

    cmd = inputs["csr_commit_cmd"]
    addr = inputs["csr_commit_addr"]
    wdata = inputs["csr_commit_wdata"] & MASK64
    commit_valid = inputs["csr_commit_valid"]

    write_req = csr_cmd_writes(cmd, wdata)
    write_legal = (
        commit_valid and write_req and csr_supported(addr) and (not csr_read_only(addr))
    )

    if write_legal:
        old = read_model(nxt, addr)
        if cmd in (CSR_CMD_RW, CSR_CMD_RWI):
            new = wdata
        elif cmd in (CSR_CMD_RS, CSR_CMD_RSI):
            new = old | wdata
        elif cmd in (CSR_CMD_RC, CSR_CMD_RCI):
            new = old & (~wdata & MASK64)
        else:
            new = old

        new = apply_mask(addr, new)

        if addr == CSR_MSTATUS:
            nxt["mstatus"] = new
        elif addr == CSR_MIE:
            nxt["mie"] = new
        elif addr == CSR_MTVEC:
            nxt["mtvec"] = new
        elif addr == CSR_MSCRATCH:
            nxt["mscratch"] = new
        elif addr == CSR_MEPC:
            nxt["mepc"] = new
        elif addr == CSR_MCAUSE:
            nxt["mcause"] = new
        elif addr == CSR_MTVAL:
            nxt["mtval"] = new
        elif addr == CSR_MIP:
            nxt["mip"] = new
        elif addr == CSR_MCYCLE:
            nxt["mcycle"] = new
        elif addr == CSR_MINSTRET:
            nxt["minstret"] = new

    if inputs["trap_update_valid"]:
        nxt["mstatus"] = inputs["trap_mstatus_new"] & MSTATUS_MASK
        nxt["mepc"] = inputs["trap_mepc"] & ~0x3
        nxt["mcause"] = inputs["trap_mcause"] & MASK64
        nxt["mtval"] = inputs["trap_mtval"] & MASK64

    if inputs["mret_update_valid"]:
        nxt["mstatus"] = inputs["mret_mstatus_new"] & MSTATUS_MASK

    nxt["mcycle"] = (nxt["mcycle"] + 1) & MASK64
    if inputs["inc_minstret"]:
        nxt["minstret"] = (nxt["minstret"] + 1) & MASK64

    return nxt


def drive_defaults(dut) -> None:
    dut.csr_req_valid.value = 0
    dut.csr_req_addr.value = 0
    dut.csr_req_cmd.value = CSR_CMD_NONE
    dut.csr_req_wdata.value = 0

    dut.csr_commit_valid.value = 0
    dut.csr_commit_addr.value = 0
    dut.csr_commit_cmd.value = CSR_CMD_NONE
    dut.csr_commit_wdata.value = 0

    dut.trap_update_valid.value = 0
    dut.trap_mepc.value = 0
    dut.trap_mcause.value = 0
    dut.trap_mtval.value = 0
    dut.trap_mstatus_new.value = 0

    dut.mret_update_valid.value = 0
    dut.mret_mstatus_new.value = 0

    dut.inc_minstret.value = 0


async def reset_dut(dut) -> None:
    drive_defaults(dut)
    dut.rst.value = 1
    await ClockCycles(dut.clk, 5)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


async def read_csr_req(
    dut, addr: int, cmd: int = CSR_CMD_NONE, wdata: int = 0
) -> tuple[int, int]:
    dut.csr_req_valid.value = 1
    dut.csr_req_addr.value = addr
    dut.csr_req_cmd.value = cmd
    dut.csr_req_wdata.value = wdata & MASK64
    await Timer(1, unit="ns")
    data = int(dut.csr_req_rdata.value) & MASK64
    illegal = int(dut.csr_req_illegal.value)
    dut.csr_req_valid.value = 0
    return data, illegal


@cocotb.test()
async def test_csr_file_directed(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    # Baseline reads.
    data, illegal = await read_csr_req(dut, CSR_MSTATUS)
    assert illegal == 0
    assert data == 0

    data, illegal = await read_csr_req(dut, CSR_MISA)
    assert illegal == 0
    assert data == MISA_RV64I

    # Read-only write should be flagged illegal.
    _, illegal = await read_csr_req(dut, CSR_MISA, CSR_CMD_RW, 0x1234)
    assert illegal == 1

    # CSRRW write to mstatus (masked).
    dut.csr_commit_valid.value = 1
    dut.csr_commit_addr.value = CSR_MSTATUS
    dut.csr_commit_cmd.value = CSR_CMD_RW
    dut.csr_commit_wdata.value = MASK64
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.csr_commit_valid.value = 0

    data, illegal = await read_csr_req(dut, CSR_MSTATUS)
    assert illegal == 0
    assert data == MSTATUS_MASK

    # CSRRS with zero operand must not write.
    before = data
    dut.csr_commit_valid.value = 1
    dut.csr_commit_addr.value = CSR_MSTATUS
    dut.csr_commit_cmd.value = CSR_CMD_RS
    dut.csr_commit_wdata.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.csr_commit_valid.value = 0

    data, _ = await read_csr_req(dut, CSR_MSTATUS)
    assert data == before

    # mepc write is aligned.
    dut.csr_commit_valid.value = 1
    dut.csr_commit_addr.value = CSR_MEPC
    dut.csr_commit_cmd.value = CSR_CMD_RW
    dut.csr_commit_wdata.value = 0x123
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.csr_commit_valid.value = 0

    data, _ = await read_csr_req(dut, CSR_MEPC)
    assert data == 0x120

    # Trap update overrides mepc/mcause/mtval/mstatus.
    dut.trap_update_valid.value = 1
    dut.trap_mepc.value = 0x105
    dut.trap_mcause.value = 2
    dut.trap_mtval.value = 0xDEAD_BEEF
    dut.trap_mstatus_new.value = 0xFFFF_FFFF_FFFF_FFFF
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.trap_update_valid.value = 0

    data, _ = await read_csr_req(dut, CSR_MEPC)
    assert data == 0x104
    data, _ = await read_csr_req(dut, CSR_MCAUSE)
    assert data == 2
    data, _ = await read_csr_req(dut, CSR_MTVAL)
    assert data == 0xDEAD_BEEF
    data, _ = await read_csr_req(dut, CSR_MSTATUS)
    assert data == MSTATUS_MASK

    # mret update only changes mstatus.
    dut.mret_update_valid.value = 1
    dut.mret_mstatus_new.value = 0x80
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.mret_update_valid.value = 0

    data, _ = await read_csr_req(dut, CSR_MSTATUS)
    assert data == 0x80


@cocotb.test()
async def test_csr_file_randomized_model(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)
    random.seed(64)

    state = {
        "mstatus": 0,
        "mie": 0,
        "mtvec": 0,
        "mscratch": 0,
        "mepc": 0,
        "mcause": 0,
        "mtval": 0,
        "mip": 0,
        "mcycle": 1,
        "minstret": 0,
    }

    csr_addrs = [
        CSR_MSTATUS,
        CSR_MISA,
        CSR_MIE,
        CSR_MTVEC,
        CSR_MSCRATCH,
        CSR_MEPC,
        CSR_MCAUSE,
        CSR_MTVAL,
        CSR_MIP,
        CSR_MVENDORID,
        CSR_MARCHID,
        CSR_MIMPID,
        CSR_MHARTID,
        CSR_MCYCLE,
        CSR_MINSTRET,
    ]

    cmds = [
        CSR_CMD_NONE,
        CSR_CMD_RW,
        CSR_CMD_RS,
        CSR_CMD_RC,
        CSR_CMD_RWI,
        CSR_CMD_RSI,
        CSR_CMD_RCI,
    ]

    for _ in range(4000):
        req_addr = (
            random.choice(csr_addrs)
            if random.getrandbits(1)
            else random.getrandbits(12)
        )
        req_cmd = random.choice(cmds)
        req_wdata = random.getrandbits(64)
        req_valid = random.getrandbits(1)

        dut.csr_req_valid.value = req_valid
        dut.csr_req_addr.value = req_addr
        dut.csr_req_cmd.value = req_cmd
        dut.csr_req_wdata.value = req_wdata
        await Timer(1, unit="ns")

        exp_req_data = read_model(state, req_addr)
        exp_req_illegal = (
            1
            if (
                req_valid
                and (
                    (not csr_supported(req_addr))
                    or (csr_cmd_writes(req_cmd, req_wdata) and csr_read_only(req_addr))
                )
            )
            else 0
        )

        got_req_data = int(dut.csr_req_rdata.value) & MASK64
        got_req_illegal = int(dut.csr_req_illegal.value)
        assert got_req_data == exp_req_data
        assert got_req_illegal == exp_req_illegal

        inputs = {
            "csr_commit_valid": random.getrandbits(1),
            "csr_commit_addr": random.choice(csr_addrs)
            if random.getrandbits(1)
            else random.getrandbits(12),
            "csr_commit_cmd": random.choice(cmds),
            "csr_commit_wdata": random.getrandbits(64),
            "trap_update_valid": 1 if random.randrange(32) == 0 else 0,
            "trap_mepc": random.getrandbits(64),
            "trap_mcause": random.getrandbits(64),
            "trap_mtval": random.getrandbits(64),
            "trap_mstatus_new": random.getrandbits(64),
            "mret_update_valid": 1 if random.randrange(32) == 1 else 0,
            "mret_mstatus_new": random.getrandbits(64),
            "inc_minstret": random.getrandbits(1),
        }

        dut.csr_commit_valid.value = inputs["csr_commit_valid"]
        dut.csr_commit_addr.value = inputs["csr_commit_addr"]
        dut.csr_commit_cmd.value = inputs["csr_commit_cmd"]
        dut.csr_commit_wdata.value = inputs["csr_commit_wdata"]
        dut.trap_update_valid.value = inputs["trap_update_valid"]
        dut.trap_mepc.value = inputs["trap_mepc"]
        dut.trap_mcause.value = inputs["trap_mcause"]
        dut.trap_mtval.value = inputs["trap_mtval"]
        dut.trap_mstatus_new.value = inputs["trap_mstatus_new"]
        dut.mret_update_valid.value = inputs["mret_update_valid"]
        dut.mret_mstatus_new.value = inputs["mret_mstatus_new"]
        dut.inc_minstret.value = inputs["inc_minstret"]

        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        state = update_state(state, inputs)

        assert (int(dut.csr_mstatus.value) & MASK64) == state["mstatus"]
        assert (int(dut.csr_mie.value) & MASK64) == state["mie"]
        assert (int(dut.csr_mtvec.value) & MASK64) == state["mtvec"]
        assert (int(dut.csr_mepc.value) & MASK64) == state["mepc"]
