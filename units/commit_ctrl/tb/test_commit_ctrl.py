import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

MCAUSE_ILLEGAL_INSTR = 2
MCAUSE_BREAKPOINT = 3
MCAUSE_ECALL_MMODE = 11


def model(**kwargs) -> dict[str, int]:
    wb_valid = kwargs["wb_valid"]
    wb_pc = kwargs["wb_pc"] & MASK64
    wb_instr = kwargs["wb_instr"] & 0xFFFF_FFFF
    wb_reg_write = kwargs["wb_reg_write"]
    wb_is_csr = kwargs["wb_is_csr"]

    wb_trap_illegal = kwargs["wb_trap_illegal"]
    wb_trap_ecall = kwargs["wb_trap_ecall"]
    wb_trap_ebreak = kwargs["wb_trap_ebreak"]
    wb_is_mret = kwargs["wb_is_mret"]
    csr_access_illegal = kwargs["csr_access_illegal"]

    trap_illegal_effective = wb_trap_illegal or (wb_is_csr and csr_access_illegal)

    trap_enter_valid = 0
    trap_cause = 0
    trap_tval = 0

    if wb_valid:
        if trap_illegal_effective:
            trap_enter_valid = 1
            trap_cause = MCAUSE_ILLEGAL_INSTR
            trap_tval = wb_instr
        elif wb_trap_ebreak:
            trap_enter_valid = 1
            trap_cause = MCAUSE_BREAKPOINT
            trap_tval = 0
        elif wb_trap_ecall:
            trap_enter_valid = 1
            trap_cause = MCAUSE_ECALL_MMODE
            trap_tval = 0

    return {
        "wb_allow_reg_write": 1
        if (wb_valid and wb_reg_write and not trap_enter_valid)
        else 0,
        "retire_valid": 1 if (wb_valid and not trap_enter_valid) else 0,
        "csr_commit_valid": 1
        if (wb_valid and wb_is_csr and not trap_enter_valid)
        else 0,
        "csr_commit_cmd": kwargs["wb_csr_cmd"] & 0x7,
        "csr_commit_addr": kwargs["wb_csr_addr"] & 0xFFF,
        "csr_commit_wdata": kwargs["wb_csr_wdata"] & MASK64,
        "trap_enter_valid": trap_enter_valid,
        "trap_cause": trap_cause,
        "trap_tval": trap_tval,
        "trap_pc": wb_pc,
        "mret_valid": 1 if (wb_valid and wb_is_mret and not trap_enter_valid) else 0,
    }


async def check_case(dut, **kwargs) -> None:
    for field, value in kwargs.items():
        getattr(dut, field).value = value

    await Timer(1, unit="ns")

    exp = model(**kwargs)

    scalar_fields = (
        "wb_allow_reg_write",
        "retire_valid",
        "csr_commit_valid",
        "trap_enter_valid",
        "mret_valid",
    )
    for field in scalar_fields:
        got = int(getattr(dut, field).value)
        assert got == exp[field], f"{field}: expected {exp[field]} got {got}"

    wide_fields = (
        "csr_commit_cmd",
        "csr_commit_addr",
        "csr_commit_wdata",
        "trap_cause",
        "trap_tval",
        "trap_pc",
    )
    for field in wide_fields:
        got = int(getattr(dut, field).value) & MASK64
        assert got == exp[field], f"{field}: expected 0x{exp[field]:x} got 0x{got:x}"


@cocotb.test()
async def test_commit_ctrl_directed(dut):
    vectors = [
        {
            "wb_valid": 0,
            "wb_pc": 0,
            "wb_instr": 0,
            "wb_reg_write": 0,
            "wb_is_csr": 0,
            "wb_csr_cmd": 0,
            "wb_csr_addr": 0,
            "wb_csr_wdata": 0,
            "wb_trap_illegal": 0,
            "wb_trap_ecall": 0,
            "wb_trap_ebreak": 0,
            "wb_is_mret": 0,
            "csr_access_illegal": 0,
        },
        {
            # Normal ALU retire.
            "wb_valid": 1,
            "wb_pc": 0x40,
            "wb_instr": 0x00A00093,
            "wb_reg_write": 1,
            "wb_is_csr": 0,
            "wb_csr_cmd": 0,
            "wb_csr_addr": 0,
            "wb_csr_wdata": 0,
            "wb_trap_illegal": 0,
            "wb_trap_ecall": 0,
            "wb_trap_ebreak": 0,
            "wb_is_mret": 0,
            "csr_access_illegal": 0,
        },
        {
            # Legal CSR commit.
            "wb_valid": 1,
            "wb_pc": 0x44,
            "wb_instr": 0x30011073,
            "wb_reg_write": 1,
            "wb_is_csr": 1,
            "wb_csr_cmd": 2,
            "wb_csr_addr": 0x300,
            "wb_csr_wdata": 0x8,
            "wb_trap_illegal": 0,
            "wb_trap_ecall": 0,
            "wb_trap_ebreak": 0,
            "wb_is_mret": 0,
            "csr_access_illegal": 0,
        },
        {
            # Illegal instruction trap.
            "wb_valid": 1,
            "wb_pc": 0x80,
            "wb_instr": 0x00000000,
            "wb_reg_write": 0,
            "wb_is_csr": 0,
            "wb_csr_cmd": 0,
            "wb_csr_addr": 0,
            "wb_csr_wdata": 0,
            "wb_trap_illegal": 1,
            "wb_trap_ecall": 0,
            "wb_trap_ebreak": 0,
            "wb_is_mret": 0,
            "csr_access_illegal": 0,
        },
        {
            # CSR access illegal trap.
            "wb_valid": 1,
            "wb_pc": 0x84,
            "wb_instr": 0x30101073,
            "wb_reg_write": 1,
            "wb_is_csr": 1,
            "wb_csr_cmd": 1,
            "wb_csr_addr": 0x301,
            "wb_csr_wdata": 1,
            "wb_trap_illegal": 0,
            "wb_trap_ecall": 0,
            "wb_trap_ebreak": 0,
            "wb_is_mret": 0,
            "csr_access_illegal": 1,
        },
        {
            # ECALL trap.
            "wb_valid": 1,
            "wb_pc": 0x88,
            "wb_instr": 0x00000073,
            "wb_reg_write": 0,
            "wb_is_csr": 0,
            "wb_csr_cmd": 0,
            "wb_csr_addr": 0,
            "wb_csr_wdata": 0,
            "wb_trap_illegal": 0,
            "wb_trap_ecall": 1,
            "wb_trap_ebreak": 0,
            "wb_is_mret": 0,
            "csr_access_illegal": 0,
        },
        {
            # MRET retire path.
            "wb_valid": 1,
            "wb_pc": 0x8C,
            "wb_instr": 0x30200073,
            "wb_reg_write": 0,
            "wb_is_csr": 0,
            "wb_csr_cmd": 0,
            "wb_csr_addr": 0,
            "wb_csr_wdata": 0,
            "wb_trap_illegal": 0,
            "wb_trap_ecall": 0,
            "wb_trap_ebreak": 0,
            "wb_is_mret": 1,
            "csr_access_illegal": 0,
        },
    ]

    for vec in vectors:
        await check_case(dut, **vec)


@cocotb.test()
async def test_commit_ctrl_randomized(dut):
    random.seed(64)

    for _ in range(20_000):
        await check_case(
            dut,
            wb_valid=random.getrandbits(1),
            wb_pc=random.getrandbits(64),
            wb_instr=random.getrandbits(32),
            wb_reg_write=random.getrandbits(1),
            wb_is_csr=random.getrandbits(1),
            wb_csr_cmd=random.getrandbits(3),
            wb_csr_addr=random.getrandbits(12),
            wb_csr_wdata=random.getrandbits(64),
            wb_trap_illegal=random.getrandbits(1),
            wb_trap_ecall=random.getrandbits(1),
            wb_trap_ebreak=random.getrandbits(1),
            wb_is_mret=random.getrandbits(1),
            csr_access_illegal=random.getrandbits(1),
        )
