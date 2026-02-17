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
LUI = 0b0110111
AUIPC = 0b0010111
JAL = 0b1101111
JALR = 0b1100111
SYSTEM = 0b1110011
FENCE = 0b0001111
F7_M_EXT = 0b0000001

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

SRC_REG = 0
SRC_IMM = 1


def ctrl_tuple(
    alu_op=ALU_ADD,
    alu_src=SRC_REG,
    mem_read=0,
    mem_write=0,
    reg_write=0,
    mem_to_reg=0,
    branch=0,
    jump=0,
    is_word_op=0,
):
    return (
        alu_op,
        alu_src,
        mem_read,
        mem_write,
        reg_write,
        mem_to_reg,
        branch,
        jump,
        is_word_op,
    )


def model_ctrl(opcode: int, funct3: int, funct7: int) -> tuple[int, ...]:
    ctrl = list(ctrl_tuple())
    valid = True

    if opcode == OP:
        ctrl[4] = 1  # reg_write
        if funct3 == 0b000:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_ADD
            elif funct7 == 0b0100000:
                ctrl[0] = ALU_SUB
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b001:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SLL
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b010:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SLT
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b011:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SLTU
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b100:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_XOR
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b101:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SRL
            elif funct7 == 0b0100000:
                ctrl[0] = ALU_SRA
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b110:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_OR
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b111:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_AND
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        else:
            valid = False

    elif opcode == OP_32:
        ctrl[4] = 1
        ctrl[8] = 1
        if funct3 == 0b000:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_ADD
            elif funct7 == 0b0100000:
                ctrl[0] = ALU_SUB
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b001:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SLL
            else:
                valid = False
        elif funct3 == 0b100:
            if funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 == 0b101:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SRL
            elif funct7 == 0b0100000:
                ctrl[0] = ALU_SRA
            elif funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        elif funct3 in (0b110, 0b111):
            if funct7 == F7_M_EXT:
                ctrl[0] = ALU_ADD
            else:
                valid = False
        else:
            valid = False

    elif opcode == OP_IMM:
        ctrl[1] = SRC_IMM
        ctrl[4] = 1
        if funct3 == 0b000:
            ctrl[0] = ALU_ADD
        elif funct3 == 0b001:
            if ((funct7 >> 1) & 0x3F) == 0:
                ctrl[0] = ALU_SLL
            else:
                valid = False
        elif funct3 == 0b010:
            ctrl[0] = ALU_SLT
        elif funct3 == 0b011:
            ctrl[0] = ALU_SLTU
        elif funct3 == 0b100:
            ctrl[0] = ALU_XOR
        elif funct3 == 0b101:
            top = (funct7 >> 1) & 0x3F
            if top == 0b000000:
                ctrl[0] = ALU_SRL
            elif top == 0b010000:
                ctrl[0] = ALU_SRA
            else:
                valid = False
        elif funct3 == 0b110:
            ctrl[0] = ALU_OR
        elif funct3 == 0b111:
            ctrl[0] = ALU_AND
        else:
            valid = False

    elif opcode == OP_IMM_32:
        ctrl[1] = SRC_IMM
        ctrl[4] = 1
        ctrl[8] = 1
        if funct3 == 0b000:
            ctrl[0] = ALU_ADD
        elif funct3 == 0b001:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SLL
            else:
                valid = False
        elif funct3 == 0b101:
            if funct7 == 0b0000000:
                ctrl[0] = ALU_SRL
            elif funct7 == 0b0100000:
                ctrl[0] = ALU_SRA
            else:
                valid = False
        else:
            valid = False

    elif opcode == LOAD:
        if funct3 in (0b000, 0b001, 0b010, 0b011, 0b100, 0b101, 0b110):
            ctrl[1] = SRC_IMM
            ctrl[2] = 1
            ctrl[4] = 1
            ctrl[5] = 1
        else:
            valid = False

    elif opcode == STORE:
        if funct3 in (0b000, 0b001, 0b010, 0b011):
            ctrl[1] = SRC_IMM
            ctrl[3] = 1
        else:
            valid = False

    elif opcode == BRANCH:
        if funct3 in (0b000, 0b001, 0b100, 0b101, 0b110, 0b111):
            ctrl[0] = ALU_SUB
            ctrl[6] = 1
        else:
            valid = False

    elif opcode == LUI:
        ctrl[1] = SRC_IMM
        ctrl[4] = 1

    elif opcode == AUIPC:
        ctrl[1] = SRC_IMM
        ctrl[4] = 1

    elif opcode == JAL:
        ctrl[1] = SRC_IMM
        ctrl[4] = 1
        ctrl[7] = 1

    elif opcode == JALR:
        if funct3 == 0b000:
            ctrl[1] = SRC_IMM
            ctrl[4] = 1
            ctrl[7] = 1
        else:
            valid = False

    elif opcode == SYSTEM:
        if funct3 == 0b000:
            pass
        elif funct3 in (0b001, 0b010, 0b011, 0b101, 0b110, 0b111):
            ctrl[4] = 1
        else:
            valid = False

    elif opcode == FENCE:
        if funct3 != 0b000:
            valid = False

    else:
        valid = False

    if not valid:
        return ctrl_tuple()

    return tuple(ctrl)


async def drive(dut, opcode: int, funct3: int, funct7: int) -> None:
    dut.opcode.value = opcode & 0x7F
    dut.funct3.value = funct3 & 0x7
    dut.funct7.value = funct7 & 0x7F
    await Timer(1, unit="ns")


def read_ctrl(dut) -> tuple[int, ...]:
    return (
        int(dut.alu_op.value),
        int(dut.alu_src.value),
        int(dut.mem_read.value),
        int(dut.mem_write.value),
        int(dut.reg_write.value),
        int(dut.mem_to_reg.value),
        int(dut.branch.value),
        int(dut.jump.value),
        int(dut.is_word_op.value),
    )


async def check(
    dut, opcode: int, funct3: int, funct7: int, expected: tuple[int, ...], name: str
) -> None:
    await drive(dut, opcode, funct3, funct7)
    got = read_ctrl(dut)
    assert got == expected, (
        f"{name}: opcode={opcode:07b} funct3={funct3:03b} funct7={funct7:07b} "
        f"expected={expected} got={got}"
    )


@cocotb.test()
async def test_directed_control_decode(dut):
    vectors = [
        ("ADD", OP, 0b000, 0b0000000, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("SUB", OP, 0b000, 0b0100000, ctrl_tuple(alu_op=ALU_SUB, reg_write=1)),
        ("AND", OP, 0b111, 0b0000000, ctrl_tuple(alu_op=ALU_AND, reg_write=1)),
        ("SRL", OP, 0b101, 0b0000000, ctrl_tuple(alu_op=ALU_SRL, reg_write=1)),
        ("SRA", OP, 0b101, 0b0100000, ctrl_tuple(alu_op=ALU_SRA, reg_write=1)),
        ("MUL", OP, 0b000, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("MULH", OP, 0b001, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("MULHSU", OP, 0b010, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("MULHU", OP, 0b011, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("DIV", OP, 0b100, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("DIVU", OP, 0b101, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("REM", OP, 0b110, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        ("REMU", OP, 0b111, F7_M_EXT, ctrl_tuple(alu_op=ALU_ADD, reg_write=1)),
        (
            "ADDW",
            OP_32,
            0b000,
            0b0000000,
            ctrl_tuple(alu_op=ALU_ADD, reg_write=1, is_word_op=1),
        ),
        (
            "SRAW",
            OP_32,
            0b101,
            0b0100000,
            ctrl_tuple(alu_op=ALU_SRA, reg_write=1, is_word_op=1),
        ),
        (
            "MULW",
            OP_32,
            0b000,
            F7_M_EXT,
            ctrl_tuple(alu_op=ALU_ADD, reg_write=1, is_word_op=1),
        ),
        (
            "DIVW",
            OP_32,
            0b100,
            F7_M_EXT,
            ctrl_tuple(alu_op=ALU_ADD, reg_write=1, is_word_op=1),
        ),
        (
            "DIVUW",
            OP_32,
            0b101,
            F7_M_EXT,
            ctrl_tuple(alu_op=ALU_ADD, reg_write=1, is_word_op=1),
        ),
        (
            "REMW",
            OP_32,
            0b110,
            F7_M_EXT,
            ctrl_tuple(alu_op=ALU_ADD, reg_write=1, is_word_op=1),
        ),
        (
            "REMUW",
            OP_32,
            0b111,
            F7_M_EXT,
            ctrl_tuple(alu_op=ALU_ADD, reg_write=1, is_word_op=1),
        ),
        (
            "ADDI",
            OP_IMM,
            0b000,
            0b0000000,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "SLTI",
            OP_IMM,
            0b010,
            0b0000000,
            ctrl_tuple(alu_op=ALU_SLT, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "SLTIU",
            OP_IMM,
            0b011,
            0b0000000,
            ctrl_tuple(alu_op=ALU_SLTU, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "XORI",
            OP_IMM,
            0b100,
            0b0000000,
            ctrl_tuple(alu_op=ALU_XOR, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "ORI",
            OP_IMM,
            0b110,
            0b0000000,
            ctrl_tuple(alu_op=ALU_OR, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "ANDI",
            OP_IMM,
            0b111,
            0b0000000,
            ctrl_tuple(alu_op=ALU_AND, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "SLLI_SHAMT63",
            OP_IMM,
            0b001,
            0b0000001,
            ctrl_tuple(alu_op=ALU_SLL, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "SRLI_SHAMT63",
            OP_IMM,
            0b101,
            0b0000001,
            ctrl_tuple(alu_op=ALU_SRL, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "SRAI_SHAMT63",
            OP_IMM,
            0b101,
            0b0100001,
            ctrl_tuple(alu_op=ALU_SRA, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "ADDIW",
            OP_IMM_32,
            0b000,
            0b0000000,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, reg_write=1, is_word_op=1),
        ),
        (
            "SLLIW",
            OP_IMM_32,
            0b001,
            0b0000000,
            ctrl_tuple(alu_op=ALU_SLL, alu_src=SRC_IMM, reg_write=1, is_word_op=1),
        ),
        (
            "SRAIW",
            OP_IMM_32,
            0b101,
            0b0100000,
            ctrl_tuple(alu_op=ALU_SRA, alu_src=SRC_IMM, reg_write=1, is_word_op=1),
        ),
        (
            "LB",
            LOAD,
            0b000,
            0,
            ctrl_tuple(
                alu_op=ALU_ADD, alu_src=SRC_IMM, mem_read=1, reg_write=1, mem_to_reg=1
            ),
        ),
        (
            "LH",
            LOAD,
            0b001,
            0,
            ctrl_tuple(
                alu_op=ALU_ADD, alu_src=SRC_IMM, mem_read=1, reg_write=1, mem_to_reg=1
            ),
        ),
        (
            "LW",
            LOAD,
            0b010,
            0,
            ctrl_tuple(
                alu_op=ALU_ADD, alu_src=SRC_IMM, mem_read=1, reg_write=1, mem_to_reg=1
            ),
        ),
        (
            "LD",
            LOAD,
            0b011,
            0,
            ctrl_tuple(
                alu_op=ALU_ADD, alu_src=SRC_IMM, mem_read=1, reg_write=1, mem_to_reg=1
            ),
        ),
        (
            "LBU",
            LOAD,
            0b100,
            0,
            ctrl_tuple(
                alu_op=ALU_ADD, alu_src=SRC_IMM, mem_read=1, reg_write=1, mem_to_reg=1
            ),
        ),
        (
            "LHU",
            LOAD,
            0b101,
            0,
            ctrl_tuple(
                alu_op=ALU_ADD, alu_src=SRC_IMM, mem_read=1, reg_write=1, mem_to_reg=1
            ),
        ),
        (
            "LWU",
            LOAD,
            0b110,
            0,
            ctrl_tuple(
                alu_op=ALU_ADD, alu_src=SRC_IMM, mem_read=1, reg_write=1, mem_to_reg=1
            ),
        ),
        (
            "SB",
            STORE,
            0b000,
            0,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, mem_write=1),
        ),
        (
            "SH",
            STORE,
            0b001,
            0,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, mem_write=1),
        ),
        (
            "SW",
            STORE,
            0b010,
            0,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, mem_write=1),
        ),
        (
            "SD",
            STORE,
            0b011,
            0,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, mem_write=1),
        ),
        ("BEQ", BRANCH, 0b000, 0, ctrl_tuple(alu_op=ALU_SUB, branch=1)),
        ("BNE", BRANCH, 0b001, 0, ctrl_tuple(alu_op=ALU_SUB, branch=1)),
        ("BLT", BRANCH, 0b100, 0, ctrl_tuple(alu_op=ALU_SUB, branch=1)),
        ("BGE", BRANCH, 0b101, 0, ctrl_tuple(alu_op=ALU_SUB, branch=1)),
        ("BLTU", BRANCH, 0b110, 0, ctrl_tuple(alu_op=ALU_SUB, branch=1)),
        ("BGEU", BRANCH, 0b111, 0, ctrl_tuple(alu_op=ALU_SUB, branch=1)),
        ("LUI", LUI, 0, 0, ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, reg_write=1)),
        (
            "AUIPC",
            AUIPC,
            0,
            0,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, reg_write=1),
        ),
        (
            "JAL",
            JAL,
            0,
            0,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, reg_write=1, jump=1),
        ),
        (
            "JALR",
            JALR,
            0b000,
            0,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_IMM, reg_write=1, jump=1),
        ),
        ("ECALL_EBREAK_CLASS", SYSTEM, 0b000, 0b0000000, ctrl_tuple()),
        (
            "CSRRW_CLASS",
            SYSTEM,
            0b001,
            0b0000000,
            ctrl_tuple(alu_op=ALU_ADD, alu_src=SRC_REG, reg_write=1),
        ),
        ("FENCE_NOP", FENCE, 0b000, 0, ctrl_tuple()),
    ]

    for name, opcode, funct3, funct7, expected in vectors:
        await check(dut, opcode, funct3, funct7, expected, name)


@cocotb.test()
async def test_invalid_combinations_zero_controls(dut):
    vectors = [
        ("UNKNOWN_OPCODE", 0b0000000, 0b000, 0b0000000),
        ("OP_BAD_FUNCT7", OP, 0b001, 0b0100000),
        ("OP32_BAD_FUNCT3", OP_32, 0b100, 0b0000000),
        ("OP32_M_BAD_FUNCT3", OP_32, 0b001, F7_M_EXT),
        ("OPIMM_BAD_SLLI", OP_IMM, 0b001, 0b0000010),
        ("OPIMM32_BAD_SHIFT", OP_IMM_32, 0b101, 0b0110000),
        ("LOAD_BAD_FUNCT3", LOAD, 0b111, 0),
        ("STORE_BAD_FUNCT3", STORE, 0b100, 0),
        ("BRANCH_BAD_FUNCT3", BRANCH, 0b010, 0),
        ("JALR_BAD_FUNCT3", JALR, 0b001, 0),
        ("SYSTEM_BAD_FUNCT3", SYSTEM, 0b100, 0),
        ("FENCE_BAD_FUNCT3", FENCE, 0b001, 0),
    ]

    for name, opcode, funct3, funct7 in vectors:
        await check(dut, opcode, funct3, funct7, ctrl_tuple(), name)


@cocotb.test()
async def test_randomized_against_model(dut):
    random.seed(64)

    for _ in range(10_000):
        opcode = random.getrandbits(7)
        funct3 = random.getrandbits(3)
        funct7 = random.getrandbits(7)

        expected = model_ctrl(opcode, funct3, funct7)
        await check(dut, opcode, funct3, funct7, expected, "RAND")
