import random

import cocotb
from cocotb.triggers import Timer

OP = 0b0110011
OP_IMM = 0b0010011
OP_32 = 0b0111011
OP_IMM_32 = 0b0011011
LOAD = 0b0000011
STORE = 0b0100011
BRANCH = 0b1100011
JALR = 0b1100111
SYSTEM = 0b1110011


def opcode_uses_rs1(opcode: int) -> bool:
    return opcode in {OP, OP_32, STORE, BRANCH, OP_IMM, OP_IMM_32, LOAD, JALR}


def opcode_uses_rs2(opcode: int) -> bool:
    return opcode in {OP, OP_32, STORE, BRANCH}


def model_load_use_stall(
    id_ex_valid: int,
    id_ex_mem_read: int,
    id_ex_is_csr: int,
    id_ex_rd: int,
    if_id_valid: int,
    if_id_opcode: int,
    if_id_funct3: int,
    if_id_rs1: int,
    if_id_rs2: int,
) -> int:
    if not id_ex_valid:
        return 0
    if not (id_ex_mem_read or id_ex_is_csr):
        return 0
    if not if_id_valid:
        return 0
    if id_ex_rd == 0:
        return 0

    uses_rs1 = opcode_uses_rs1(if_id_opcode)
    uses_rs2 = opcode_uses_rs2(if_id_opcode)

    if if_id_opcode == SYSTEM:
        uses_rs1 = if_id_funct3 in {0b001, 0b010, 0b011}
        uses_rs2 = False

    rs1_hazard = uses_rs1 and (id_ex_rd == if_id_rs1)
    rs2_hazard = uses_rs2 and (id_ex_rd == if_id_rs2)
    return 1 if (rs1_hazard or rs2_hazard) else 0


async def check_case(
    dut,
    *,
    id_ex_valid: int,
    id_ex_mem_read: int,
    id_ex_is_csr: int,
    id_ex_rd: int,
    if_id_valid: int,
    if_id_opcode: int,
    if_id_funct3: int,
    if_id_rs1: int,
    if_id_rs2: int,
    name: str,
) -> None:
    dut.id_ex_valid.value = id_ex_valid
    dut.id_ex_mem_read.value = id_ex_mem_read
    dut.id_ex_is_csr.value = id_ex_is_csr
    dut.id_ex_rd.value = id_ex_rd
    dut.if_id_valid.value = if_id_valid
    dut.if_id_opcode.value = if_id_opcode
    dut.if_id_funct3.value = if_id_funct3
    dut.if_id_rs1.value = if_id_rs1
    dut.if_id_rs2.value = if_id_rs2
    await Timer(1, unit="ns")

    expected = model_load_use_stall(
        id_ex_valid,
        id_ex_mem_read,
        id_ex_is_csr,
        id_ex_rd,
        if_id_valid,
        if_id_opcode,
        if_id_funct3,
        if_id_rs1,
        if_id_rs2,
    )
    got = int(dut.load_use_stall.value)
    assert got == expected, f"{name}: load_use_stall expected {expected} got {got}"


@cocotb.test()
async def test_hazard_unit_directed(dut):
    vectors = [
        {
            "name": "NO_HAZARD_IDLE",
            "id_ex_valid": 0,
            "id_ex_mem_read": 0,
            "id_ex_is_csr": 0,
            "id_ex_rd": 0,
            "if_id_valid": 0,
            "if_id_opcode": OP,
            "if_id_funct3": 0,
            "if_id_rs1": 0,
            "if_id_rs2": 0,
        },
        {
            "name": "RS1_HAZARD_OP_IMM",
            "id_ex_valid": 1,
            "id_ex_mem_read": 1,
            "id_ex_is_csr": 0,
            "id_ex_rd": 5,
            "if_id_valid": 1,
            "if_id_opcode": OP_IMM,
            "if_id_funct3": 0b000,
            "if_id_rs1": 5,
            "if_id_rs2": 31,
        },
        {
            "name": "RS2_HAZARD_BRANCH",
            "id_ex_valid": 1,
            "id_ex_mem_read": 1,
            "id_ex_is_csr": 0,
            "id_ex_rd": 9,
            "if_id_valid": 1,
            "if_id_opcode": BRANCH,
            "if_id_funct3": 0b000,
            "if_id_rs1": 1,
            "if_id_rs2": 9,
        },
        {
            "name": "NO_FALSE_RS2_HAZARD_OP_IMM",
            "id_ex_valid": 1,
            "id_ex_mem_read": 1,
            "id_ex_is_csr": 0,
            "id_ex_rd": 7,
            "if_id_valid": 1,
            "if_id_opcode": OP_IMM,
            "if_id_funct3": 0b000,
            "if_id_rs1": 2,
            "if_id_rs2": 7,
        },
        {
            "name": "NO_STALL_ON_X0_DEST",
            "id_ex_valid": 1,
            "id_ex_mem_read": 1,
            "id_ex_is_csr": 0,
            "id_ex_rd": 0,
            "if_id_valid": 1,
            "if_id_opcode": OP,
            "if_id_funct3": 0b000,
            "if_id_rs1": 0,
            "if_id_rs2": 0,
        },
        {
            "name": "NO_STALL_NON_LOAD",
            "id_ex_valid": 1,
            "id_ex_mem_read": 0,
            "id_ex_is_csr": 0,
            "id_ex_rd": 5,
            "if_id_valid": 1,
            "if_id_opcode": OP,
            "if_id_funct3": 0b000,
            "if_id_rs1": 5,
            "if_id_rs2": 5,
        },
        {
            "name": "NO_STALL_IF_ID_INVALID",
            "id_ex_valid": 1,
            "id_ex_mem_read": 1,
            "id_ex_is_csr": 0,
            "id_ex_rd": 5,
            "if_id_valid": 0,
            "if_id_opcode": OP,
            "if_id_funct3": 0b000,
            "if_id_rs1": 5,
            "if_id_rs2": 5,
        },
        {
            "name": "SYSTEM_CSRRW_RS1_HAZARD",
            "id_ex_valid": 1,
            "id_ex_mem_read": 1,
            "id_ex_is_csr": 0,
            "id_ex_rd": 12,
            "if_id_valid": 1,
            "if_id_opcode": SYSTEM,
            "if_id_funct3": 0b001,
            "if_id_rs1": 12,
            "if_id_rs2": 0,
        },
        {
            "name": "SYSTEM_CSRRSI_NO_RS1_HAZARD",
            "id_ex_valid": 1,
            "id_ex_mem_read": 1,
            "id_ex_is_csr": 0,
            "id_ex_rd": 9,
            "if_id_valid": 1,
            "if_id_opcode": SYSTEM,
            "if_id_funct3": 0b110,
            "if_id_rs1": 9,
            "if_id_rs2": 0,
        },
        {
            "name": "CSR_PRODUCER_RS1_HAZARD",
            "id_ex_valid": 1,
            "id_ex_mem_read": 0,
            "id_ex_is_csr": 1,
            "id_ex_rd": 26,
            "if_id_valid": 1,
            "if_id_opcode": OP_IMM,
            "if_id_funct3": 0b000,
            "if_id_rs1": 26,
            "if_id_rs2": 0,
        },
    ]

    for vec in vectors:
        await check_case(dut, **vec)


@cocotb.test()
async def test_hazard_unit_randomized(dut):
    random.seed(64)
    opcodes = [OP, OP_IMM, OP_32, OP_IMM_32, LOAD, STORE, BRANCH, JALR, SYSTEM]

    for idx in range(20_000):
        if random.getrandbits(1):
            if_id_opcode = random.choice(opcodes)
        else:
            if_id_opcode = random.getrandbits(7)

        await check_case(
            dut,
            id_ex_valid=random.getrandbits(1),
            id_ex_mem_read=random.getrandbits(1),
            id_ex_is_csr=random.getrandbits(1),
            id_ex_rd=random.getrandbits(5),
            if_id_valid=random.getrandbits(1),
            if_id_opcode=if_id_opcode,
            if_id_funct3=random.getrandbits(3),
            if_id_rs1=random.getrandbits(5),
            if_id_rs2=random.getrandbits(5),
            name=f"RAND_{idx}",
        )
