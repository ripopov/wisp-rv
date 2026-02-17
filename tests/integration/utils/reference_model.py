from __future__ import annotations

from dataclasses import dataclass

MASK64 = (1 << 64) - 1

OP_LUI = 0x37
OP_AUIPC = 0x17
OP_JAL = 0x6F
OP_JALR = 0x67
OP_BRANCH = 0x63
OP_LOAD = 0x03
OP_STORE = 0x23
OP_IMM = 0x13
OP_REG = 0x33


def _sign_extend(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    mask = (1 << bits) - 1
    value &= mask
    return (value ^ sign) - sign


def _to_u64(value: int) -> int:
    return value & MASK64


def _to_s64(value: int) -> int:
    value &= MASK64
    if value & (1 << 63):
        return value - (1 << 64)
    return value


def _div_trunc_zero(dividend: int, divisor: int) -> int:
    sign = -1 if (dividend < 0) ^ (divisor < 0) else 1
    return sign * (abs(dividend) // abs(divisor))


def _rem_trunc_zero(dividend: int, divisor: int) -> int:
    return dividend - _div_trunc_zero(dividend, divisor) * divisor


def _read_u32(mem: dict[int, int], addr: int) -> int:
    return (
        (mem.get(addr + 0, 0) << 0)
        | (mem.get(addr + 1, 0) << 8)
        | (mem.get(addr + 2, 0) << 16)
        | (mem.get(addr + 3, 0) << 24)
    ) & 0xFFFF_FFFF


def _read_u64(mem: dict[int, int], addr: int) -> int:
    value = 0
    for i in range(8):
        value |= (mem.get(addr + i, 0) & 0xFF) << (8 * i)
    return value & MASK64


def _write_u64(mem: dict[int, int], addr: int, value: int) -> None:
    value &= MASK64
    for i in range(8):
        mem[addr + i] = (value >> (8 * i)) & 0xFF


@dataclass(frozen=True)
class ReferenceRunResult:
    regs: tuple[int, ...]
    memory: dict[int, int]
    retired_pcs: tuple[int, ...]
    steps: int
    final_pc: int
    tohost: int


class Rv64ReferenceModel:
    def __init__(self) -> None:
        self._regs = [0] * 32
        self._pc = 0
        self._memory: dict[int, int] = {}
        self._retired: list[int] = []

    def run(
        self,
        *,
        initial_pc: int,
        memory: dict[int, int],
        max_steps: int,
        tohost_addr: int = 0x200,
        stop_on_tohost: bool = True,
    ) -> ReferenceRunResult:
        self._regs = [0] * 32
        self._pc = initial_pc & MASK64
        self._memory = dict(memory)
        self._retired = []

        for step in range(max_steps):
            pc = self._pc
            instr = _read_u32(self._memory, pc)
            self._retired.append(pc)
            self._step(instr)

            tohost = _read_u64(self._memory, tohost_addr)
            if stop_on_tohost and tohost != 0:
                return ReferenceRunResult(
                    regs=tuple(self._regs),
                    memory=dict(self._memory),
                    retired_pcs=tuple(self._retired),
                    steps=step + 1,
                    final_pc=self._pc,
                    tohost=tohost,
                )

        raise RuntimeError(
            f"Reference model exceeded max_steps={max_steps}; pc=0x{self._pc:016x}"
        )

    def _step(self, instr: int) -> None:
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F

        next_pc = _to_u64(self._pc + 4)

        if opcode == OP_LUI:
            imm_u = instr & 0xFFFF_F000
            self._wr(rd, imm_u)
        elif opcode == OP_AUIPC:
            imm_u = instr & 0xFFFF_F000
            self._wr(rd, _to_u64(self._pc + imm_u))
        elif opcode == OP_JAL:
            imm_j = (
                (((instr >> 31) & 0x1) << 20)
                | (((instr >> 21) & 0x3FF) << 1)
                | (((instr >> 20) & 0x1) << 11)
                | (((instr >> 12) & 0xFF) << 12)
            )
            offset = _sign_extend(imm_j, 21)
            self._wr(rd, next_pc)
            next_pc = _to_u64(self._pc + offset)
        elif opcode == OP_JALR:
            imm_i = _sign_extend(instr >> 20, 12)
            base = self._regs[rs1]
            self._wr(rd, next_pc)
            next_pc = _to_u64((base + imm_i) & ~1)
        elif opcode == OP_BRANCH:
            imm_b = (
                (((instr >> 31) & 0x1) << 12)
                | (((instr >> 25) & 0x3F) << 5)
                | (((instr >> 8) & 0xF) << 1)
                | (((instr >> 7) & 0x1) << 11)
            )
            offset = _sign_extend(imm_b, 13)
            lhs = self._regs[rs1]
            rhs = self._regs[rs2]

            take = False
            if funct3 == 0x0:
                take = lhs == rhs
            elif funct3 == 0x1:
                take = lhs != rhs
            elif funct3 == 0x4:
                take = _to_s64(lhs) < _to_s64(rhs)
            elif funct3 == 0x5:
                take = _to_s64(lhs) >= _to_s64(rhs)
            elif funct3 == 0x6:
                take = lhs < rhs
            elif funct3 == 0x7:
                take = lhs >= rhs
            else:
                raise ValueError(f"Unsupported BRANCH funct3=0x{funct3:x}")

            if take:
                next_pc = _to_u64(self._pc + offset)
        elif opcode == OP_LOAD:
            imm_i = _sign_extend(instr >> 20, 12)
            addr = _to_u64(self._regs[rs1] + imm_i)

            if funct3 == 0x3:  # LD
                self._wr(rd, _read_u64(self._memory, addr))
            elif funct3 == 0x2:  # LW
                word = _read_u32(self._memory, addr)
                self._wr(rd, _sign_extend(word, 32))
            else:
                raise ValueError(f"Unsupported LOAD funct3=0x{funct3:x}")
        elif opcode == OP_STORE:
            imm_s = (((instr >> 25) & 0x7F) << 5) | ((instr >> 7) & 0x1F)
            imm = _sign_extend(imm_s, 12)
            addr = _to_u64(self._regs[rs1] + imm)
            value = self._regs[rs2]

            if funct3 == 0x3:  # SD
                _write_u64(self._memory, addr, value)
            elif funct3 == 0x2:  # SW
                for i in range(4):
                    self._memory[addr + i] = (value >> (8 * i)) & 0xFF
            else:
                raise ValueError(f"Unsupported STORE funct3=0x{funct3:x}")
        elif opcode == OP_IMM:
            imm_i = _sign_extend(instr >> 20, 12)
            lhs = self._regs[rs1]

            if funct3 == 0x0:  # ADDI
                self._wr(rd, lhs + imm_i)
            elif funct3 == 0x4:  # XORI
                self._wr(rd, lhs ^ imm_i)
            elif funct3 == 0x6:  # ORI
                self._wr(rd, lhs | imm_i)
            elif funct3 == 0x7:  # ANDI
                self._wr(rd, lhs & imm_i)
            elif funct3 == 0x1:  # SLLI
                shamt = (instr >> 20) & 0x3F
                if (funct7 & 0x7E) != 0x00:
                    raise ValueError(f"Unsupported OP-IMM SLLI funct7=0x{funct7:x}")
                self._wr(rd, lhs << shamt)
            elif funct3 == 0x5:
                shamt = (instr >> 20) & 0x3F
                funct7_base = funct7 & 0x7E
                if funct7_base == 0x00:  # SRLI
                    self._wr(rd, lhs >> shamt)
                elif funct7_base == 0x20:  # SRAI
                    self._wr(rd, _to_s64(lhs) >> shamt)
                else:
                    raise ValueError(f"Unsupported OP-IMM shift funct7=0x{funct7:x}")
            else:
                raise ValueError(f"Unsupported OP-IMM funct3=0x{funct3:x}")
        elif opcode == OP_REG:
            lhs = self._regs[rs1]
            rhs = self._regs[rs2]

            if funct7 == 0x00:
                if funct3 == 0x0:  # ADD
                    self._wr(rd, lhs + rhs)
                elif funct3 == 0x1:  # SLL
                    self._wr(rd, lhs << (rhs & 0x3F))
                elif funct3 == 0x2:  # SLT
                    self._wr(rd, int(_to_s64(lhs) < _to_s64(rhs)))
                elif funct3 == 0x3:  # SLTU
                    self._wr(rd, int(lhs < rhs))
                elif funct3 == 0x4:  # XOR
                    self._wr(rd, lhs ^ rhs)
                elif funct3 == 0x5:  # SRL
                    self._wr(rd, lhs >> (rhs & 0x3F))
                elif funct3 == 0x6:  # OR
                    self._wr(rd, lhs | rhs)
                elif funct3 == 0x7:  # AND
                    self._wr(rd, lhs & rhs)
                else:
                    raise ValueError(f"Unsupported OP funct3=0x{funct3:x}")
            elif funct7 == 0x20:
                if funct3 == 0x0:  # SUB
                    self._wr(rd, lhs - rhs)
                elif funct3 == 0x5:  # SRA
                    self._wr(rd, _to_s64(lhs) >> (rhs & 0x3F))
                else:
                    raise ValueError(
                        f"Unsupported OP funct3=0x{funct3:x} with funct7=0x20"
                    )
            elif funct7 == 0x01:
                # M-extension subset used by current integration programs.
                if funct3 == 0x0:  # MUL
                    self._wr(rd, (lhs * rhs) & MASK64)
                elif funct3 == 0x4:  # DIV
                    dividend = _to_s64(lhs)
                    divisor = _to_s64(rhs)
                    if divisor == 0:
                        self._wr(rd, MASK64)
                    elif dividend == -(1 << 63) and divisor == -1:
                        self._wr(rd, dividend)
                    else:
                        self._wr(rd, _div_trunc_zero(dividend, divisor))
                elif funct3 == 0x6:  # REM
                    dividend = _to_s64(lhs)
                    divisor = _to_s64(rhs)
                    if divisor == 0:
                        self._wr(rd, dividend)
                    elif dividend == -(1 << 63) and divisor == -1:
                        self._wr(rd, 0)
                    else:
                        self._wr(rd, _rem_trunc_zero(dividend, divisor))
                else:
                    raise ValueError(f"Unsupported M-extension funct3=0x{funct3:x}")
            else:
                raise ValueError(f"Unsupported OP funct7=0x{funct7:x}")
        else:
            raise ValueError(
                f"Unsupported opcode 0x{opcode:02x} at pc=0x{self._pc:016x} instr=0x{instr:08x}"
            )

        self._pc = next_pc
        self._regs[0] = 0

    def _wr(self, rd: int, value: int) -> None:
        if rd != 0:
            self._regs[rd] = _to_u64(value)
