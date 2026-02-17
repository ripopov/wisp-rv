import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1
MSTATUS_MASK = 0x1888


def model(
    trap_enter_valid: int,
    trap_cause: int,
    trap_tval: int,
    trap_pc: int,
    mret_valid: int,
    csr_mstatus: int,
    csr_mtvec: int,
    csr_mepc: int,
) -> dict[str, int]:
    out = {
        "redirect_valid": 0,
        "redirect_pc": 0,
        "trap_update_valid": 0,
        "trap_mepc": 0,
        "trap_mcause": 0,
        "trap_mtval": 0,
        "trap_mstatus_new": csr_mstatus & MSTATUS_MASK,
        "mret_update_valid": 0,
        "mret_mstatus_new": csr_mstatus & MSTATUS_MASK,
    }

    old_mie = (csr_mstatus >> 3) & 1
    old_mpie = (csr_mstatus >> 7) & 1

    if trap_enter_valid:
        out["redirect_valid"] = 1
        out["redirect_pc"] = csr_mtvec & ~0x3
        out["trap_update_valid"] = 1
        out["trap_mepc"] = trap_pc & ~0x3
        out["trap_mcause"] = trap_cause & MASK64
        out["trap_mtval"] = trap_tval & MASK64

        mstatus = csr_mstatus & MSTATUS_MASK
        mstatus &= ~(1 << 7)
        mstatus |= old_mie << 7
        mstatus &= ~(1 << 3)
        mstatus &= ~(0b11 << 11)
        mstatus |= 0b11 << 11
        out["trap_mstatus_new"] = mstatus & MASK64
    elif mret_valid:
        out["redirect_valid"] = 1
        out["redirect_pc"] = csr_mepc & ~0x3
        out["mret_update_valid"] = 1

        mstatus = csr_mstatus & MSTATUS_MASK
        mstatus &= ~(1 << 3)
        mstatus |= old_mpie << 3
        mstatus |= 1 << 7
        mstatus &= ~(0b11 << 11)
        out["mret_mstatus_new"] = mstatus & MASK64

    return out


async def check_case(dut, **kwargs) -> None:
    dut.trap_enter_valid.value = kwargs["trap_enter_valid"]
    dut.trap_cause.value = kwargs["trap_cause"] & MASK64
    dut.trap_tval.value = kwargs["trap_tval"] & MASK64
    dut.trap_pc.value = kwargs["trap_pc"] & MASK64
    dut.mret_valid.value = kwargs["mret_valid"]
    dut.csr_mstatus.value = kwargs["csr_mstatus"] & MASK64
    dut.csr_mtvec.value = kwargs["csr_mtvec"] & MASK64
    dut.csr_mepc.value = kwargs["csr_mepc"] & MASK64
    await Timer(1, unit="ns")

    exp = model(**kwargs)

    for field in (
        "redirect_valid",
        "trap_update_valid",
        "mret_update_valid",
    ):
        got = int(getattr(dut, field).value)
        assert got == exp[field], f"{field}: expected {exp[field]} got {got}"

    for field in (
        "redirect_pc",
        "trap_mepc",
        "trap_mcause",
        "trap_mtval",
        "trap_mstatus_new",
        "mret_mstatus_new",
    ):
        got = int(getattr(dut, field).value) & MASK64
        assert got == exp[field], f"{field}: expected 0x{exp[field]:x} got 0x{got:x}"


@cocotb.test()
async def test_trap_ctrl_directed(dut):
    vectors = [
        {
            "trap_enter_valid": 0,
            "trap_cause": 0,
            "trap_tval": 0,
            "trap_pc": 0,
            "mret_valid": 0,
            "csr_mstatus": 0,
            "csr_mtvec": 0x100,
            "csr_mepc": 0x200,
        },
        {
            "trap_enter_valid": 1,
            "trap_cause": 2,
            "trap_tval": 0xDEAD,
            "trap_pc": 0x123,
            "mret_valid": 0,
            "csr_mstatus": 0x8,
            "csr_mtvec": 0x401,
            "csr_mepc": 0,
        },
        {
            "trap_enter_valid": 0,
            "trap_cause": 0,
            "trap_tval": 0,
            "trap_pc": 0,
            "mret_valid": 1,
            "csr_mstatus": 0x80,
            "csr_mtvec": 0,
            "csr_mepc": 0x345,
        },
        {
            # trap takes priority over mret.
            "trap_enter_valid": 1,
            "trap_cause": 11,
            "trap_tval": 0,
            "trap_pc": 0x88,
            "mret_valid": 1,
            "csr_mstatus": 0x1888,
            "csr_mtvec": 0x222,
            "csr_mepc": 0x444,
        },
    ]

    for vec in vectors:
        await check_case(dut, **vec)


@cocotb.test()
async def test_trap_ctrl_randomized(dut):
    random.seed(64)

    for _ in range(10_000):
        await check_case(
            dut,
            trap_enter_valid=random.getrandbits(1),
            trap_cause=random.getrandbits(64),
            trap_tval=random.getrandbits(64),
            trap_pc=random.getrandbits(64),
            mret_valid=random.getrandbits(1),
            csr_mstatus=random.getrandbits(64),
            csr_mtvec=random.getrandbits(64),
            csr_mepc=random.getrandbits(64),
        )
