import random

import cocotb
from cocotb.triggers import Timer

MASK64 = (1 << 64) - 1

OP = 0b0110011
OP_IMM = 0b0010011
OP_32 = 0b0111011
OP_IMM_32 = 0b0011011
LOAD = 0b0000011
STORE = 0b0100011
BRANCH = 0b1100011
LUI = 0b0110111
AUIPC = 0b0010111
JAL = 0b1101111
JALR = 0b1100111

ALU_ADD = 0x0
ALU_SUB = 0x1
ALU_AND = 0x2
ALU_OR = 0x3
ALU_XOR = 0x4
ALU_SLT = 0x5
ALU_SLTU = 0x6
ALU_SLL = 0x7
ALU_SRL = 0x8
ALU_SRA = 0x9


def as_signed_64(value: int) -> int:
    value &= MASK64
    if value & (1 << 63):
        return value - (1 << 64)
    return value


def sign_extend_32(value: int) -> int:
    value &= 0xFFFF_FFFF
    if value & 0x8000_0000:
        value |= 0xFFFF_FFFF_0000_0000
    return value & MASK64


def model_alu(a: int, b: int, alu_op: int) -> int:
    a_u = a & MASK64
    b_u = b & MASK64

    if alu_op == ALU_ADD:
        return (a_u + b_u) & MASK64
    if alu_op == ALU_SUB:
        return (a_u - b_u) & MASK64
    if alu_op == ALU_AND:
        return a_u & b_u
    if alu_op == ALU_OR:
        return a_u | b_u
    if alu_op == ALU_XOR:
        return a_u ^ b_u
    if alu_op == ALU_SLT:
        return 1 if as_signed_64(a_u) < as_signed_64(b_u) else 0
    if alu_op == ALU_SLTU:
        return 1 if a_u < b_u else 0
    if alu_op == ALU_SLL:
        return (a_u << (b_u & 0x3F)) & MASK64
    if alu_op == ALU_SRL:
        return (a_u >> (b_u & 0x3F)) & MASK64
    if alu_op == ALU_SRA:
        return (as_signed_64(a_u) >> (b_u & 0x3F)) & MASK64
    return 0


def model_branch(rs1_data: int, rs2_data: int, funct3: int, branch: int) -> int:
    if not branch:
        return 0

    rs1_u = rs1_data & MASK64
    rs2_u = rs2_data & MASK64
    rs1_s = as_signed_64(rs1_data)
    rs2_s = as_signed_64(rs2_data)

    if funct3 == 0b000:
        return int(rs1_u == rs2_u)
    if funct3 == 0b001:
        return int(rs1_u != rs2_u)
    if funct3 == 0b100:
        return int(rs1_s < rs2_s)
    if funct3 == 0b101:
        return int(rs1_s >= rs2_s)
    if funct3 == 0b110:
        return int(rs1_u < rs2_u)
    if funct3 == 0b111:
        return int(rs1_u >= rs2_u)
    return 0


def model_ex_stage(
    pc: int,
    rs1_data: int,
    rs2_data: int,
    imm: int,
    opcode: int,
    funct3: int,
    alu_op: int,
    alu_src: int,
    branch: int,
    jump: int,
    is_word_op: int,
) -> tuple[int, int, int]:
    pc_u = pc & MASK64
    rs1_u = rs1_data & MASK64
    rs2_u = rs2_data & MASK64
    imm_u = imm & MASK64

    if opcode == LUI:
        alu_a = 0
    elif opcode in (AUIPC, JAL, JALR):
        alu_a = pc_u
    else:
        alu_a = rs1_u

    if jump:
        alu_b = 4
    elif alu_src:
        alu_b = imm_u
    else:
        alu_b = rs2_u

    if is_word_op and alu_op in (ALU_SLL, ALU_SRL, ALU_SRA):
        alu_b_eff = alu_b & 0x1F
    else:
        alu_b_eff = alu_b

    alu_raw = model_alu(alu_a, alu_b_eff, alu_op)
    jump_link_addr = (pc_u + 4) & MASK64

    result = jump_link_addr if jump else alu_raw
    if is_word_op:
        result = sign_extend_32(result)

    is_jalr = 1 if opcode == JALR else 0
    jump_target = (
        (((rs1_u + imm_u) & MASK64) & ~0x1) if is_jalr else ((pc_u + imm_u) & MASK64)
    )
    branch_target = jump_target if jump else ((pc_u + imm_u) & MASK64)

    branch_taken = 1 if jump else model_branch(rs1_u, rs2_u, funct3, branch)
    return result & MASK64, int(branch_taken), branch_target & MASK64


async def check_case(
    dut,
    pc: int,
    rs1_data: int,
    rs2_data: int,
    imm: int,
    opcode: int,
    funct3: int,
    alu_op: int,
    alu_src: int,
    branch: int,
    jump: int,
    is_word_op: int,
    name: str,
) -> None:
    dut.pc.value = pc & MASK64
    dut.rs1_data.value = rs1_data & MASK64
    dut.rs2_data.value = rs2_data & MASK64
    dut.imm.value = imm & MASK64
    dut.opcode.value = opcode & 0x7F
    dut.funct3.value = funct3 & 0x7
    dut.alu_op.value = alu_op & 0xF
    dut.alu_src.value = alu_src & 0x1
    dut.branch.value = branch & 0x1
    dut.jump.value = jump & 0x1
    dut.is_word_op.value = is_word_op & 0x1
    await Timer(1, unit="ns")

    exp_result, exp_branch_taken, exp_branch_target = model_ex_stage(
        pc,
        rs1_data,
        rs2_data,
        imm,
        opcode,
        funct3,
        alu_op,
        alu_src,
        branch,
        jump,
        is_word_op,
    )

    got_result = int(dut.alu_result.value) & MASK64
    got_branch_taken = int(dut.branch_taken.value)
    got_branch_target = int(dut.branch_target.value) & MASK64

    assert got_result == exp_result, f"{name}: alu_result mismatch"
    assert got_branch_taken == exp_branch_taken, f"{name}: branch_taken mismatch"
    assert got_branch_target == exp_branch_target, f"{name}: branch_target mismatch"


@cocotb.test()
async def test_ex_stage_directed(dut):
    max_pos = 0x7FFF_FFFF_FFFF_FFFF
    min_neg = 0x8000_0000_0000_0000

    vectors = [
        # Core ALU operand mux classes.
        ("R_ADD", 0x100, 5, 7, 0x1234, OP, 0, ALU_ADD, 0, 0, 0, 0),
        (
            "I_ADDI",
            0x100,
            5,
            0xDEAD,
            0xFFFF_FFFF_FFFF_FFFE,
            OP_IMM,
            0,
            ALU_ADD,
            1,
            0,
            0,
            0,
        ),
        ("LOAD_ADDR", 0x100, 0x1000, 0x777, 0x20, LOAD, 0, ALU_ADD, 1, 0, 0, 0),
        ("STORE_ADDR", 0x100, 0x2000, 0x8888, 0x30, STORE, 0, ALU_ADD, 1, 0, 0, 0),
        (
            "LUI_MUX",
            0x100,
            0xABCD,
            0x1234,
            0xFFFF_FFFF_8000_1000,
            LUI,
            0,
            ALU_ADD,
            1,
            0,
            0,
            0,
        ),
        (
            "AUIPC_MUX",
            0x2000,
            0xABCD,
            0x1234,
            0x0000_0000_0000_0100,
            AUIPC,
            0,
            ALU_ADD,
            1,
            0,
            0,
            0,
        ),
        # Branch condition coverage.
        ("BEQ_TAKEN", 0x3000, 0x55, 0x55, 0x10, BRANCH, 0b000, ALU_SUB, 0, 1, 0, 0),
        ("BNE_TAKEN", 0x3000, 0x55, 0x77, 0x14, BRANCH, 0b001, ALU_SUB, 0, 1, 0, 0),
        (
            "BLT_SIGNED",
            0x3000,
            min_neg,
            max_pos,
            0x18,
            BRANCH,
            0b100,
            ALU_SUB,
            0,
            1,
            0,
            0,
        ),
        (
            "BGE_SIGNED",
            0x3000,
            max_pos,
            min_neg,
            0x1C,
            BRANCH,
            0b101,
            ALU_SUB,
            0,
            1,
            0,
            0,
        ),
        (
            "BLTU_UNSIGNED",
            0x3000,
            0x0,
            0xFFFF_FFFF_FFFF_FFFF,
            0x20,
            BRANCH,
            0b110,
            ALU_SUB,
            0,
            1,
            0,
            0,
        ),
        (
            "BGEU_UNSIGNED",
            0x3000,
            0xFFFF_FFFF_FFFF_FFFF,
            0x1,
            0x24,
            BRANCH,
            0b111,
            ALU_SUB,
            0,
            1,
            0,
            0,
        ),
        # Jump/link behavior.
        ("JAL_LINK_TARGET", 0x4000, 0xAAAA, 0xBBBB, 0x100, JAL, 0, ALU_ADD, 1, 0, 1, 0),
        ("JALR_MASK_TARGET", 0x5000, 0x2001, 0xBBBB, 0x8, JALR, 0, ALU_ADD, 1, 0, 1, 0),
        # W-suffix sign extension behavior.
        ("ADDW_POS", 0x0, 1, 2, 0, OP_32, 0, ALU_ADD, 0, 0, 0, 1),
        ("ADDW_NEG", 0x0, 0x0000_0000_7FFF_FFFF, 1, 0, OP_32, 0, ALU_ADD, 0, 0, 0, 1),
        ("SUBW_NEG", 0x0, 0, 1, 0, OP_32, 0, ALU_SUB, 0, 0, 0, 1),
        ("SLLW_SHAMT5_MASK", 0x0, 1, 32, 0, OP_32, 0, ALU_SLL, 0, 0, 0, 1),
        ("SRLW_EDGE", 0x0, 0x0000_0000_8000_0000, 1, 0, OP_32, 0, ALU_SRL, 0, 0, 0, 1),
        ("SRAW_EDGE", 0x0, 0xFFFF_FFFF_8000_0000, 1, 0, OP_32, 0, ALU_SRA, 0, 0, 0, 1),
    ]

    for (
        name,
        pc,
        rs1_data,
        rs2_data,
        imm,
        opcode,
        funct3,
        alu_op,
        alu_src,
        branch,
        jump,
        is_word_op,
    ) in vectors:
        await check_case(
            dut,
            pc,
            rs1_data,
            rs2_data,
            imm,
            opcode,
            funct3,
            alu_op,
            alu_src,
            branch,
            jump,
            is_word_op,
            name,
        )


@cocotb.test()
async def test_ex_stage_randomized(dut):
    random.seed(64)

    opcode_choices = [
        OP,
        OP_IMM,
        OP_32,
        OP_IMM_32,
        LOAD,
        STORE,
        BRANCH,
        LUI,
        AUIPC,
        JAL,
        JALR,
        0,
        0x7F,
    ]

    for idx in range(10_000):
        pc = random.getrandbits(64)
        rs1_data = random.getrandbits(64)
        rs2_data = random.getrandbits(64)
        imm = random.getrandbits(64)
        opcode = random.choice(opcode_choices)
        funct3 = random.getrandbits(3)
        alu_op = random.getrandbits(4)
        alu_src = random.getrandbits(1)
        branch = random.getrandbits(1)
        jump = random.getrandbits(1)
        is_word_op = random.getrandbits(1)

        await check_case(
            dut,
            pc,
            rs1_data,
            rs2_data,
            imm,
            opcode,
            funct3,
            alu_op,
            alu_src,
            branch,
            jump,
            is_word_op,
            f"RAND_{idx}",
        )
