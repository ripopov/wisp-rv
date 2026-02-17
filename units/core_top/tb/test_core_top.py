import random
from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadWrite, RisingEdge, Timer

MASK64 = (1 << 64) - 1

OP_IMM = 0b0010011
LOAD = 0b0000011
STORE = 0b0100011
BRANCH = 0b1100011
LUI = 0b0110111
AUIPC = 0b0010111
JAL = 0b1101111
JALR = 0b1100111
SYSTEM = 0b1110011

F3_BEQ = 0b000
F3_LD = 0b011
F3_SD = 0b011
F3_CSRRW = 0b001
F3_CSRRS = 0b010
F3_CSRRC = 0b011
F3_CSRRWI = 0b101
F3_CSRRSI = 0b110
F3_CSRRCI = 0b111

CSR_MSTATUS = 0x300
CSR_MIE = 0x304
CSR_MTVEC = 0x305
CSR_MSCRATCH = 0x340
CSR_MEPC = 0x341
CSR_MCAUSE = 0x342
CSR_MTVAL = 0x343
CSR_MCYCLE = 0xB00
CSR_MINSTRET = 0xB02
CSR_MVENDORID = 0xF11

SYSTEM_IMM_ECALL = 0x000
SYSTEM_IMM_MRET = 0x302

NOP = 0x00000013
TOHOST_ADDR = 0x200


def u64(value: int) -> int:
    return value & MASK64


def read_u64(memory: dict[int, int], addr: int) -> int:
    value = 0
    for i in range(8):
        value |= (memory.get(addr + i, 0) & 0xFF) << (8 * i)
    return value & MASK64


def write_u64(memory: dict[int, int], addr: int, wdata: int, byte_en: int) -> None:
    for i in range(8):
        if (byte_en >> i) & 1:
            memory[addr + i] = (wdata >> (8 * i)) & 0xFF


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


def enc_b(offset: int, rs2: int, rs1: int, funct3: int, opcode: int) -> int:
    if (offset & 0x1) != 0:
        raise ValueError(f"Branch offset must be 2-byte aligned: {offset}")
    if offset < -4096 or offset > 4094:
        raise ValueError(f"Branch offset out of range: {offset}")
    imm13 = offset & 0x1FFF
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


def enc_j(offset: int, rd: int, opcode: int) -> int:
    if (offset & 0x1) != 0:
        raise ValueError(f"JAL offset must be 2-byte aligned: {offset}")
    if offset < -(1 << 20) or offset > ((1 << 20) - 2):
        raise ValueError(f"JAL offset out of range: {offset}")
    imm21 = offset & 0x1FFFFF
    return (
        (((imm21 >> 20) & 0x1) << 31)
        | (((imm21 >> 1) & 0x3FF) << 21)
        | (((imm21 >> 11) & 0x1) << 20)
        | (((imm21 >> 12) & 0xFF) << 12)
        | ((rd & 0x1F) << 7)
        | (opcode & 0x7F)
    )


class AsmBuilder:
    def __init__(self):
        self.words: list[int] = []
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str, tuple[Any, ...], str]] = []

    @property
    def pc(self) -> int:
        return len(self.words) * 4

    def label(self, name: str) -> None:
        self.labels[name] = self.pc

    def emit(self, word: int) -> None:
        self.words.append(word & 0xFFFF_FFFF)

    def nop(self) -> None:
        self.emit(NOP)

    def addi(self, rd: int, rs1: int, imm12: int) -> None:
        self.emit(enc_i(imm12, rs1, 0b000, rd, OP_IMM))

    def addi_label_delta(
        self, rd: int, rs1: int, base_label: str, target_label: str
    ) -> None:
        self.fixups.append(
            (
                len(self.words),
                "I_DELTA",
                (rd, rs1, 0b000, OP_IMM, base_label),
                target_label,
            )
        )
        self.emit(0)

    def ld(self, rd: int, rs1: int, imm12: int) -> None:
        self.emit(enc_i(imm12, rs1, F3_LD, rd, LOAD))

    def sd(self, rs2: int, rs1: int, imm12: int) -> None:
        self.emit(enc_s(imm12, rs2, rs1, F3_SD, STORE))

    def lui(self, rd: int, imm20: int) -> None:
        self.emit(enc_u(imm20, rd, LUI))

    def auipc(self, rd: int, imm20: int) -> None:
        self.emit(enc_u(imm20, rd, AUIPC))

    def beq(self, rs1: int, rs2: int, label: str) -> None:
        self.fixups.append((len(self.words), "B", (rs1, rs2, F3_BEQ, BRANCH), label))
        self.emit(0)

    def jal(self, rd: int, label: str) -> None:
        self.fixups.append((len(self.words), "J", (rd, JAL), label))
        self.emit(0)

    def jalr(self, rd: int, rs1: int, imm12: int) -> None:
        self.emit(enc_i(imm12, rs1, 0b000, rd, JALR))

    def csrrw(self, rd: int, csr: int, rs1: int) -> None:
        self.emit(enc_i(csr, rs1, F3_CSRRW, rd, SYSTEM))

    def csrrs(self, rd: int, csr: int, rs1: int) -> None:
        self.emit(enc_i(csr, rs1, F3_CSRRS, rd, SYSTEM))

    def csrrc(self, rd: int, csr: int, rs1: int) -> None:
        self.emit(enc_i(csr, rs1, F3_CSRRC, rd, SYSTEM))

    def csrrwi(self, rd: int, csr: int, zimm: int) -> None:
        self.emit(enc_i(csr, zimm, F3_CSRRWI, rd, SYSTEM))

    def csrrsi(self, rd: int, csr: int, zimm: int) -> None:
        self.emit(enc_i(csr, zimm, F3_CSRRSI, rd, SYSTEM))

    def csrrci(self, rd: int, csr: int, zimm: int) -> None:
        self.emit(enc_i(csr, zimm, F3_CSRRCI, rd, SYSTEM))

    def ecall(self) -> None:
        self.emit(enc_i(SYSTEM_IMM_ECALL, 0, 0b000, 0, SYSTEM))

    def mret(self) -> None:
        self.emit(enc_i(SYSTEM_IMM_MRET, 0, 0b000, 0, SYSTEM))

    def raw(self, word: int) -> None:
        self.emit(word)

    def resolve(self) -> list[int]:
        for idx, kind, params, label in self.fixups:
            if label not in self.labels:
                raise ValueError(f"Unknown label '{label}'")
            current_pc = idx * 4
            target_pc = self.labels[label]
            offset = target_pc - current_pc

            if kind == "B":
                rs1, rs2, funct3, opcode = params
                self.words[idx] = enc_b(offset, rs2, rs1, funct3, opcode)
            elif kind == "J":
                rd, opcode = params
                self.words[idx] = enc_j(offset, rd, opcode)
            elif kind == "I_DELTA":
                rd, rs1, funct3, opcode, base_label = params
                if base_label not in self.labels:
                    raise ValueError(f"Unknown base label '{base_label}'")
                imm = target_pc - self.labels[base_label]
                if imm < -2048 or imm > 2047:
                    raise ValueError(f"I-type immediate out of range: {imm}")
                self.words[idx] = enc_i(imm, rs1, funct3, rd, opcode)
            else:
                raise ValueError(f"Unsupported fixup kind '{kind}'")

        return list(self.words)


def build_stage8_program() -> tuple[list[int], dict[str, int]]:
    b = AsmBuilder()

    # Bring-up NOP to avoid reset/fetch edge sensitivity.
    b.nop()

    # Baseline forwarding sanity.
    b.addi(1, 0, 5)
    b.addi(2, 1, 10)
    b.sd(2, 0, 0x100)

    # Program trap vector.
    b.label("mtvec_base")
    b.auipc(20, 0)
    b.addi_label_delta(20, 20, "mtvec_base", "trap_handler")
    b.csrrw(0, CSR_MTVEC, 20)

    # CSR R/W semantics on mstatus.
    b.addi(3, 0, 0x8)
    b.csrrw(4, CSR_MSTATUS, 3)
    b.sd(4, 0, 0x108)
    b.csrrs(5, CSR_MSTATUS, 0)
    b.sd(5, 0, 0x110)
    b.csrrci(0, CSR_MSTATUS, 0x8)
    b.csrrs(6, CSR_MSTATUS, 0)
    b.sd(6, 0, 0x118)

    # CSRRS with rs1=x0 must not write.
    b.addi(7, 0, 0x80)
    b.csrrw(0, CSR_MIE, 7)
    b.csrrs(8, CSR_MIE, 0)
    b.sd(8, 0, 0x120)
    b.csrrs(9, CSR_MIE, 0)
    b.sd(9, 0, 0x128)

    # Illegal instruction trap.
    b.label("illegal_site")
    b.raw(0x00000000)
    b.label("after_illegal")
    b.csrrs(10, CSR_MCAUSE, 0)
    b.sd(10, 0, 0x130)
    b.csrrs(11, CSR_MEPC, 0)
    b.sd(11, 0, 0x138)
    b.csrrs(12, CSR_MTVAL, 0)
    b.sd(12, 0, 0x140)

    # ECALL trap.
    b.label("ecall_site")
    b.ecall()
    b.label("after_ecall")
    b.csrrs(13, CSR_MCAUSE, 0)
    b.sd(13, 0, 0x148)
    b.csrrs(14, CSR_MEPC, 0)
    b.sd(14, 0, 0x150)
    b.csrrs(15, CSR_MTVAL, 0)
    b.sd(15, 0, 0x158)
    b.csrrs(16, CSR_MSCRATCH, 0)
    b.sd(16, 0, 0x160)

    # CSR counters must advance.
    b.csrrs(17, CSR_MCYCLE, 0)
    b.sd(17, 0, 0x168)
    b.csrrs(18, CSR_MINSTRET, 0)
    b.sd(18, 0, 0x170)

    # Illegal CSR write (read-only mvendorid) must trap as illegal instruction.
    b.label("ro_write_site")
    b.csrrw(19, CSR_MVENDORID, 1)
    b.label("after_ro_write")
    b.csrrs(20, CSR_MCAUSE, 0)
    b.sd(20, 0, 0x178)
    b.csrrs(21, CSR_MEPC, 0)
    b.sd(21, 0, 0x180)
    b.csrrs(22, CSR_MTVAL, 0)
    b.sd(22, 0, 0x188)
    b.csrrs(23, CSR_MSCRATCH, 0)
    b.sd(23, 0, 0x190)

    # Completion signal.
    b.addi(24, 0, TOHOST_ADDR)
    b.addi(25, 0, 1)
    b.sd(25, 24, 0)

    b.label("spin")
    b.jal(0, "spin")

    # Trap handler: skip trapping instruction, bump trap count, return.
    b.label("trap_handler")
    b.csrrs(26, CSR_MEPC, 0)
    b.addi(26, 26, 4)
    b.csrrw(0, CSR_MEPC, 26)
    b.csrrs(27, CSR_MSCRATCH, 0)
    b.addi(27, 27, 1)
    b.csrrw(0, CSR_MSCRATCH, 27)
    b.mret()

    words = b.resolve()

    ro_write_instr = enc_i(CSR_MVENDORID, 1, F3_CSRRW, 19, SYSTEM)

    expected = {
        "forward_basic": 15,
        "mstatus_old": 0,
        "mstatus_set": 0x8,
        "mstatus_clear": 0,
        "mie_read_1": 0x80,
        "mie_read_2": 0x80,
        "illegal_cause": 2,
        "illegal_mepc": b.labels["illegal_site"] + 4,
        "illegal_mtval": 0,
        "ecall_cause": 11,
        "ecall_mepc": b.labels["ecall_site"] + 4,
        "ecall_mtval": 0,
        "trap_count_after_ecall": 2,
        "ro_write_cause": 2,
        "ro_write_mepc": b.labels["ro_write_site"] + 4,
        "ro_write_mtval": ro_write_instr,
        "final_trap_count": 3,
    }
    return words, expected


async def reset_dut(dut, cycles: int = 5) -> None:
    dut.rst.value = 1
    dut.imem_ready.value = 1
    dut.imem_rdata.value = NOP
    dut.dmem_ready.value = 1
    dut.dmem_rdata.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def run_program(
    dut,
    program_words: list[int],
    *,
    max_cycles: int,
    with_backpressure: bool,
) -> dict[int, int]:
    imem = {idx: word for idx, word in enumerate(program_words)}
    dmem: dict[int, int] = {}

    tohost_seen = False
    drain_cycles = 0
    random.seed(64)
    recent_pcs: list[int] = []
    writes: list[tuple[int, int]] = []

    for cycle in range(max_cycles):
        await ReadWrite()

        recent_pcs.append(int(dut.dbg_if_pc.value) & MASK64)
        if len(recent_pcs) > 64:
            recent_pcs.pop(0)

        imem_addr_word = (int(dut.imem_addr.value) & MASK64) >> 2
        dut.imem_ready.value = 1
        dut.imem_rdata.value = imem.get(imem_addr_word, NOP)

        if with_backpressure and int(dut.dmem_req.value):
            # Deterministic wait-state insertion while requests are active.
            dut.dmem_ready.value = 0 if (cycle % 4 == 1) else 1
        else:
            dut.dmem_ready.value = 1

        dmem_addr_aligned = (int(dut.dmem_addr.value) & MASK64) & ~0x7
        dut.dmem_rdata.value = read_u64(dmem, dmem_addr_aligned)

        await Timer(1, unit="ns")

        dmem_req = int(dut.dmem_req.value)
        dmem_we = int(dut.dmem_we.value)
        dmem_ready = int(dut.dmem_ready.value)

        if dmem_req and dmem_ready:
            addr_aligned = (int(dut.dmem_addr.value) & MASK64) & ~0x7
            wdata = int(dut.dmem_wdata.value) & MASK64
            byte_en = int(dut.dmem_byte_en.value) & 0xFF

            if dmem_we:
                write_u64(dmem, addr_aligned, wdata, byte_en)
                writes.append((addr_aligned, read_u64(dmem, addr_aligned)))

                if (addr_aligned <= TOHOST_ADDR <= addr_aligned + 7) and (
                    read_u64(dmem, TOHOST_ADDR) != 0
                ):
                    tohost_seen = True
                    drain_cycles = 8

        await RisingEdge(dut.clk)

        if tohost_seen:
            drain_cycles -= 1
            if drain_cycles == 0:
                break
    else:
        raise AssertionError(
            "Program did not signal completion via tohost before timeout"
            f"; writes={writes[-16:]}"
            f"; recent_pcs={[hex(pc) for pc in recent_pcs[-24:]]}"
        )

    return dmem


def assert_program_results(dmem: dict[int, int], expected: dict[str, int]) -> None:
    observed = {
        "forward_basic": read_u64(dmem, 0x100),
        "mstatus_old": read_u64(dmem, 0x108),
        "mstatus_set": read_u64(dmem, 0x110),
        "mstatus_clear": read_u64(dmem, 0x118),
        "mie_read_1": read_u64(dmem, 0x120),
        "mie_read_2": read_u64(dmem, 0x128),
        "illegal_cause": read_u64(dmem, 0x130),
        "illegal_mepc": read_u64(dmem, 0x138),
        "illegal_mtval": read_u64(dmem, 0x140),
        "ecall_cause": read_u64(dmem, 0x148),
        "ecall_mepc": read_u64(dmem, 0x150),
        "ecall_mtval": read_u64(dmem, 0x158),
        "trap_count_after_ecall": read_u64(dmem, 0x160),
        "mcycle_snapshot": read_u64(dmem, 0x168),
        "minstret_snapshot": read_u64(dmem, 0x170),
        "ro_write_cause": read_u64(dmem, 0x178),
        "ro_write_mepc": read_u64(dmem, 0x180),
        "ro_write_mtval": read_u64(dmem, 0x188),
        "final_trap_count": read_u64(dmem, 0x190),
        "tohost": read_u64(dmem, TOHOST_ADDR),
    }
    assert observed["forward_basic"] == expected["forward_basic"], observed
    assert observed["mstatus_old"] == expected["mstatus_old"], observed
    assert observed["mstatus_set"] == expected["mstatus_set"], observed
    assert observed["mstatus_clear"] == expected["mstatus_clear"], observed
    assert observed["mie_read_1"] == expected["mie_read_1"], observed
    assert observed["mie_read_2"] == expected["mie_read_2"], observed
    assert observed["illegal_cause"] == expected["illegal_cause"], observed
    assert observed["illegal_mepc"] == expected["illegal_mepc"], observed
    assert observed["illegal_mtval"] == expected["illegal_mtval"], observed
    assert observed["ecall_cause"] == expected["ecall_cause"], observed
    assert observed["ecall_mepc"] == expected["ecall_mepc"], observed
    assert observed["ecall_mtval"] == expected["ecall_mtval"], observed
    assert observed["trap_count_after_ecall"] == expected["trap_count_after_ecall"], (
        observed
    )
    assert observed["ro_write_cause"] == expected["ro_write_cause"], observed
    assert observed["ro_write_mepc"] == expected["ro_write_mepc"], observed
    assert observed["ro_write_mtval"] == expected["ro_write_mtval"], observed
    assert observed["final_trap_count"] == expected["final_trap_count"], observed
    assert observed["mcycle_snapshot"] > 0, observed
    assert observed["minstret_snapshot"] > 0, observed
    assert observed["mcycle_snapshot"] >= observed["minstret_snapshot"], observed
    assert observed["tohost"] == 1, observed


@cocotb.test()
async def test_core_top_stage8_program(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    program_words, expected = build_stage8_program()
    dmem = await run_program(
        dut,
        program_words,
        max_cycles=4000,
        with_backpressure=False,
    )
    assert_program_results(dmem, expected)


@cocotb.test()
async def test_core_top_stage8_program_with_backpressure(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    program_words, expected = build_stage8_program()
    dmem = await run_program(
        dut,
        program_words,
        max_cycles=8000,
        with_backpressure=True,
    )
    assert_program_results(dmem, expected)
