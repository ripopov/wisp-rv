import random

import cocotb
from cocotb.triggers import Timer

MASK32 = (1 << 32) - 1

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

FMT_R = 0
FMT_I = 1
FMT_S = 2
FMT_B = 3
FMT_U = 4
FMT_J = 5


def enc_r(funct7: int, rs2: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    return (
        ((funct7 & 0x7F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_i(imm12: int, rs1: int, funct3: int, rd: int, opcode: int) -> int:
    return (
        ((imm12 & 0xFFF) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_s(imm12: int, rs2: int, rs1: int, funct3: int, opcode: int) -> int:
    imm12 &= 0xFFF
    return (
        (((imm12 >> 5) & 0x7F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | ((imm12 & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def enc_b(imm13: int, rs2: int, rs1: int, funct3: int, opcode: int) -> int:
    imm13 &= 0x1FFF
    return (
        (((imm13 >> 12) & 0x1) << 31)
        | (((imm13 >> 5) & 0x3F) << 25)
        | ((rs2 & 0x1F) << 20)
        | ((rs1 & 0x1F) << 15)
        | ((funct3 & 0x7) << 12)
        | (((imm13 >> 1) & 0xF) << 8)
        | (((imm13 >> 11) & 0x1) << 7)
        | (opcode & 0x7F)
    )


def enc_u(imm20: int, rd: int, opcode: int) -> int:
    return ((imm20 & 0xFFFFF) << 12) | ((rd & 0x1F) << 7) | (opcode & 0x7F)


def enc_j(imm21: int, rd: int, opcode: int) -> int:
    imm21 &= 0x1FFFFF
    return (
        (((imm21 >> 20) & 0x1) << 31)
        | (((imm21 >> 1) & 0x3FF) << 21)
        | (((imm21 >> 11) & 0x1) << 20)
        | (((imm21 >> 12) & 0xFF) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


def model_decode(instr: int) -> tuple[int, int]:
    opcode = instr & 0x7F
    funct3 = (instr >> 12) & 0x7
    funct7 = (instr >> 25) & 0x7F
    rd = (instr >> 7) & 0x1F
    rs1 = (instr >> 15) & 0x1F
    imm12 = (instr >> 20) & 0xFFF

    fmt = FMT_I
    valid = False

    if opcode == OP:
        fmt = FMT_R
        if funct3 == 0b000:
            valid = funct7 in (0b0000000, 0b0100000, F7_M_EXT)
        elif funct3 in (0b001, 0b010, 0b011, 0b100, 0b110, 0b111):
            valid = funct7 in (0b0000000, F7_M_EXT)
        elif funct3 == 0b101:
            valid = funct7 in (0b0000000, 0b0100000, F7_M_EXT)
    elif opcode == OP_32:
        fmt = FMT_R
        if funct3 == 0b000:
            valid = funct7 in (0b0000000, 0b0100000, F7_M_EXT)
        elif funct3 == 0b001:
            valid = funct7 == 0b0000000
        elif funct3 == 0b100:
            valid = funct7 == F7_M_EXT
        elif funct3 == 0b101:
            valid = funct7 in (0b0000000, 0b0100000, F7_M_EXT)
        elif funct3 in (0b110, 0b111):
            valid = funct7 == F7_M_EXT
    elif opcode == OP_IMM:
        fmt = FMT_I
        if funct3 in (0b000, 0b010, 0b011, 0b100, 0b110, 0b111):
            valid = True
        elif funct3 == 0b001:
            valid = ((instr >> 26) & 0x3F) == 0b000000
        elif funct3 == 0b101:
            top = (instr >> 26) & 0x3F
            valid = top in (0b000000, 0b010000)
    elif opcode == OP_IMM_32:
        fmt = FMT_I
        if funct3 == 0b000:
            valid = True
        elif funct3 == 0b001:
            valid = funct7 == 0b0000000
        elif funct3 == 0b101:
            valid = funct7 in (0b0000000, 0b0100000)
    elif opcode == LOAD:
        fmt = FMT_I
        valid = funct3 in (0b000, 0b001, 0b010, 0b011, 0b100, 0b101, 0b110)
    elif opcode == STORE:
        fmt = FMT_S
        valid = funct3 in (0b000, 0b001, 0b010, 0b011)
    elif opcode == BRANCH:
        fmt = FMT_B
        valid = funct3 in (0b000, 0b001, 0b100, 0b101, 0b110, 0b111)
    elif opcode == LUI:
        fmt = FMT_U
        valid = True
    elif opcode == AUIPC:
        fmt = FMT_U
        valid = True
    elif opcode == JAL:
        fmt = FMT_J
        valid = True
    elif opcode == JALR:
        fmt = FMT_I
        valid = funct3 == 0b000
    elif opcode == SYSTEM:
        fmt = FMT_I
        if funct3 == 0b000:
            valid = rd == 0 and rs1 == 0 and imm12 in (0x000, 0x001, 0x302)
        else:
            valid = funct3 in (0b001, 0b010, 0b011, 0b101, 0b110, 0b111)
    elif opcode == FENCE:
        fmt = FMT_I
        valid = funct3 == 0b000

    return fmt, 0 if valid else 1


async def drive_instr(dut, instr: int) -> None:
    dut.instr.value = instr & MASK32
    await Timer(1, unit="ns")


def assert_field_extract(dut, instr: int) -> None:
    assert int(dut.opcode.value) == (instr & 0x7F)
    assert int(dut.rd.value) == ((instr >> 7) & 0x1F)
    assert int(dut.funct3.value) == ((instr >> 12) & 0x7)
    assert int(dut.rs1.value) == ((instr >> 15) & 0x1F)
    assert int(dut.rs2.value) == ((instr >> 20) & 0x1F)
    assert int(dut.funct7.value) == ((instr >> 25) & 0x7F)


@cocotb.test()
async def test_decode_all_rv64i_encodings(dut):
    valid_vectors = []

    # OP (R-type)
    valid_vectors += [
        ("ADD", enc_r(0b0000000, 9, 8, 0b000, 7, OP), FMT_R),
        ("SUB", enc_r(0b0100000, 9, 8, 0b000, 7, OP), FMT_R),
        ("SLL", enc_r(0b0000000, 9, 8, 0b001, 7, OP), FMT_R),
        ("SLT", enc_r(0b0000000, 9, 8, 0b010, 7, OP), FMT_R),
        ("SLTU", enc_r(0b0000000, 9, 8, 0b011, 7, OP), FMT_R),
        ("XOR", enc_r(0b0000000, 9, 8, 0b100, 7, OP), FMT_R),
        ("SRL", enc_r(0b0000000, 9, 8, 0b101, 7, OP), FMT_R),
        ("SRA", enc_r(0b0100000, 9, 8, 0b101, 7, OP), FMT_R),
        ("OR", enc_r(0b0000000, 9, 8, 0b110, 7, OP), FMT_R),
        ("AND", enc_r(0b0000000, 9, 8, 0b111, 7, OP), FMT_R),
        ("MUL", enc_r(F7_M_EXT, 9, 8, 0b000, 7, OP), FMT_R),
        ("MULH", enc_r(F7_M_EXT, 9, 8, 0b001, 7, OP), FMT_R),
        ("MULHSU", enc_r(F7_M_EXT, 9, 8, 0b010, 7, OP), FMT_R),
        ("MULHU", enc_r(F7_M_EXT, 9, 8, 0b011, 7, OP), FMT_R),
        ("DIV", enc_r(F7_M_EXT, 9, 8, 0b100, 7, OP), FMT_R),
        ("DIVU", enc_r(F7_M_EXT, 9, 8, 0b101, 7, OP), FMT_R),
        ("REM", enc_r(F7_M_EXT, 9, 8, 0b110, 7, OP), FMT_R),
        ("REMU", enc_r(F7_M_EXT, 9, 8, 0b111, 7, OP), FMT_R),
    ]

    # OP-32 (R-type, RV64 only)
    valid_vectors += [
        ("ADDW", enc_r(0b0000000, 9, 8, 0b000, 7, OP_32), FMT_R),
        ("SUBW", enc_r(0b0100000, 9, 8, 0b000, 7, OP_32), FMT_R),
        ("SLLW", enc_r(0b0000000, 9, 8, 0b001, 7, OP_32), FMT_R),
        ("SRLW", enc_r(0b0000000, 9, 8, 0b101, 7, OP_32), FMT_R),
        ("SRAW", enc_r(0b0100000, 9, 8, 0b101, 7, OP_32), FMT_R),
        ("MULW", enc_r(F7_M_EXT, 9, 8, 0b000, 7, OP_32), FMT_R),
        ("DIVW", enc_r(F7_M_EXT, 9, 8, 0b100, 7, OP_32), FMT_R),
        ("DIVUW", enc_r(F7_M_EXT, 9, 8, 0b101, 7, OP_32), FMT_R),
        ("REMW", enc_r(F7_M_EXT, 9, 8, 0b110, 7, OP_32), FMT_R),
        ("REMUW", enc_r(F7_M_EXT, 9, 8, 0b111, 7, OP_32), FMT_R),
    ]

    # OP-IMM (I-type)
    valid_vectors += [
        ("ADDI", enc_i(0x07F, 8, 0b000, 7, OP_IMM), FMT_I),
        ("SLTI", enc_i(0xF80, 8, 0b010, 7, OP_IMM), FMT_I),
        ("SLTIU", enc_i(0x123, 8, 0b011, 7, OP_IMM), FMT_I),
        ("XORI", enc_i(0x3A5, 8, 0b100, 7, OP_IMM), FMT_I),
        ("ORI", enc_i(0x055, 8, 0b110, 7, OP_IMM), FMT_I),
        ("ANDI", enc_i(0xAA0, 8, 0b111, 7, OP_IMM), FMT_I),
        ("SLLI", enc_i(0x03F, 8, 0b001, 7, OP_IMM), FMT_I),
        ("SRLI", enc_i(0x03F, 8, 0b101, 7, OP_IMM), FMT_I),
        ("SRAI", enc_i((0b010000 << 6) | 0x3F, 8, 0b101, 7, OP_IMM), FMT_I),
    ]

    # OP-IMM-32 (I-type, RV64 only)
    valid_vectors += [
        ("ADDIW", enc_i(0x7FF, 8, 0b000, 7, OP_IMM_32), FMT_I),
        ("SLLIW", enc_i(0x01F, 8, 0b001, 7, OP_IMM_32), FMT_I),
        ("SRLIW", enc_i(0x01F, 8, 0b101, 7, OP_IMM_32), FMT_I),
        ("SRAIW", enc_i((0b0100000 << 5) | 0x1F, 8, 0b101, 7, OP_IMM_32), FMT_I),
    ]

    # LOAD / STORE / BRANCH
    valid_vectors += [
        ("LB", enc_i(0x010, 8, 0b000, 7, LOAD), FMT_I),
        ("LH", enc_i(0x010, 8, 0b001, 7, LOAD), FMT_I),
        ("LW", enc_i(0x010, 8, 0b010, 7, LOAD), FMT_I),
        ("LD", enc_i(0x010, 8, 0b011, 7, LOAD), FMT_I),
        ("LBU", enc_i(0x010, 8, 0b100, 7, LOAD), FMT_I),
        ("LHU", enc_i(0x010, 8, 0b101, 7, LOAD), FMT_I),
        ("LWU", enc_i(0x010, 8, 0b110, 7, LOAD), FMT_I),
        ("SB", enc_s(0x055, 9, 8, 0b000, STORE), FMT_S),
        ("SH", enc_s(0x055, 9, 8, 0b001, STORE), FMT_S),
        ("SW", enc_s(0x055, 9, 8, 0b010, STORE), FMT_S),
        ("SD", enc_s(0x055, 9, 8, 0b011, STORE), FMT_S),
        ("BEQ", enc_b(0x010, 9, 8, 0b000, BRANCH), FMT_B),
        ("BNE", enc_b(0x010, 9, 8, 0b001, BRANCH), FMT_B),
        ("BLT", enc_b(0x010, 9, 8, 0b100, BRANCH), FMT_B),
        ("BGE", enc_b(0x010, 9, 8, 0b101, BRANCH), FMT_B),
        ("BLTU", enc_b(0x010, 9, 8, 0b110, BRANCH), FMT_B),
        ("BGEU", enc_b(0x010, 9, 8, 0b111, BRANCH), FMT_B),
    ]

    # U/J/System/Fence
    valid_vectors += [
        ("LUI", enc_u(0x8ABCD, 7, LUI), FMT_U),
        ("AUIPC", enc_u(0x12345, 7, AUIPC), FMT_U),
        ("JAL", enc_j(0x00100, 7, JAL), FMT_J),
        ("JALR", enc_i(0x024, 8, 0b000, 7, JALR), FMT_I),
        ("ECALL", 0x00000073, FMT_I),
        ("EBREAK", 0x00100073, FMT_I),
        ("MRET", 0x30200073, FMT_I),
        ("CSRRW", enc_i(0x300, 8, 0b001, 7, SYSTEM), FMT_I),
        ("CSRRS", enc_i(0x341, 8, 0b010, 7, SYSTEM), FMT_I),
        ("CSRRC", enc_i(0x342, 8, 0b011, 7, SYSTEM), FMT_I),
        ("CSRRWI", enc_i(0x305, 0x1F, 0b101, 7, SYSTEM), FMT_I),
        ("CSRRSI", enc_i(0x304, 0x01, 0b110, 7, SYSTEM), FMT_I),
        ("CSRRCI", enc_i(0x343, 0x1F, 0b111, 7, SYSTEM), FMT_I),
        ("FENCE", enc_i(0x033, 0, 0b000, 0, FENCE), FMT_I),
    ]

    for name, instr, exp_fmt in valid_vectors:
        await drive_instr(dut, instr)
        assert_field_extract(dut, instr)
        got_fmt = int(dut.instr_format.value)
        got_illegal = int(dut.illegal_instr.value)
        assert got_fmt == exp_fmt, f"{name}: expected format {exp_fmt}, got {got_fmt}"
        assert got_illegal == 0, f"{name}: expected legal instruction"


@cocotb.test()
async def test_illegal_instruction_detection(dut):
    illegal_vectors = [
        ("UNKNOWN_OPCODE", 0x00000000),
        ("OP_BAD_FUNCT7", enc_r(0b1111111, 9, 8, 0b000, 7, OP)),
        ("OP_SLL_BAD_FUNCT7", enc_r(0b0100000, 9, 8, 0b001, 7, OP)),
        ("OP32_M_BAD_FUNCT3", enc_r(F7_M_EXT, 9, 8, 0b001, 7, OP_32)),
        ("OP_IMM_SLLI_BAD_IMM11_6", enc_i((0b000001 << 6) | 0x01, 8, 0b001, 7, OP_IMM)),
        ("OP_IMM_SRLI_BAD_IMM11_6", enc_i((0b000001 << 6) | 0x01, 8, 0b101, 7, OP_IMM)),
        ("OP_IMM_32_SLLIW_BAD", enc_i((0b0000001 << 5) | 0x01, 8, 0b001, 7, OP_IMM_32)),
        ("LOAD_BAD_FUNCT3", enc_i(0x10, 8, 0b111, 7, LOAD)),
        ("STORE_BAD_FUNCT3", enc_s(0x44, 9, 8, 0b100, STORE)),
        ("BRANCH_BAD_FUNCT3", enc_b(0x10, 9, 8, 0b010, BRANCH)),
        ("JALR_BAD_FUNCT3", enc_i(0x10, 8, 0b001, 7, JALR)),
        ("SYSTEM_BAD_IMM", enc_i(0x002, 0, 0b000, 0, SYSTEM)),
        ("SYSTEM_BAD_RD", enc_i(0x000, 0, 0b000, 1, SYSTEM)),
        ("SYSTEM_BAD_RS1", enc_i(0x001, 1, 0b000, 0, SYSTEM)),
        ("SYSTEM_BAD_FUNCT3", enc_i(0x300, 1, 0b100, 1, SYSTEM)),
        ("FENCE_I_NOT_SUPPORTED", enc_i(0x000, 0, 0b001, 0, FENCE)),
    ]

    for name, instr in illegal_vectors:
        await drive_instr(dut, instr)
        assert_field_extract(dut, instr)
        got_illegal = int(dut.illegal_instr.value)
        assert got_illegal == 1, f"{name}: expected illegal instruction"


@cocotb.test()
async def test_randomized_against_python_model(dut):
    random.seed(64)

    for _ in range(10_000):
        instr = random.getrandbits(32)
        exp_fmt, exp_illegal = model_decode(instr)

        await drive_instr(dut, instr)
        assert_field_extract(dut, instr)

        got_illegal = int(dut.illegal_instr.value)
        assert got_illegal == exp_illegal, (
            f"illegal mismatch: instr=0x{instr:08x} expected={exp_illegal} got={got_illegal}"
        )

        if exp_illegal == 0:
            got_fmt = int(dut.instr_format.value)
            assert got_fmt == exp_fmt, (
                f"format mismatch: instr=0x{instr:08x} expected={exp_fmt} got={got_fmt}"
            )
