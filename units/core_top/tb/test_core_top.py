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

F3_BEQ = 0b000
F3_LD = 0b011
F3_SD = 0b011

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


def build_stage7_program() -> tuple[list[int], dict[str, int]]:
    b = AsmBuilder()

    # Bring-up NOP to avoid reset/fetch edge sensitivity.
    b.nop()

    # EX/MEM forwarding.
    b.addi(1, 0, 5)
    b.addi(2, 1, 10)
    b.sd(2, 0, 0x100)

    # MEM/WB forwarding.
    b.addi(3, 0, 7)
    b.addi(4, 0, 1)
    b.addi(5, 3, 9)
    b.sd(5, 0, 0x108)

    # EX/MEM priority over MEM/WB.
    b.addi(6, 0, 5)
    b.addi(6, 0, 7)
    b.addi(7, 6, 10)
    b.sd(7, 0, 0x110)

    # x0 must never receive forwarded data.
    b.addi(0, 0, 5)
    b.addi(8, 0, 10)
    b.sd(8, 0, 0x118)

    # Store-data forwarding and load-use hazard stalling.
    b.addi(9, 0, 0x44)
    b.sd(9, 0, 0x120)
    b.ld(10, 0, 0x120)
    b.addi(11, 10, 1)
    b.sd(11, 0, 0x128)

    # Branch with forwarded operands + wrong-path flush.
    b.addi(12, 0, 5)
    b.addi(13, 0, 5)
    b.beq(12, 13, "branch_taken")
    b.addi(14, 0, 99)
    b.sd(14, 0, 0x158)
    b.label("branch_taken")
    b.addi(14, 0, 42)
    b.sd(14, 0, 0x130)

    # AUIPC + JALR with forwarded base + wrong-path flush.
    b.label("auipc_site")
    b.auipc(20, 0)
    b.addi_label_delta(20, 20, "auipc_site", "jalr_target")
    b.label("jalr_site")
    b.jalr(21, 20, 0)
    b.addi(22, 0, 0xDE)
    b.sd(22, 0, 0x150)
    b.label("jalr_target")
    b.addi(22, 0, 0x33)
    b.sd(22, 0, 0x138)
    b.sd(21, 0, 0x140)

    # LUI + ADDI constant build with forwarding.
    b.lui(23, 0x12345)
    b.addi(23, 23, 0x678)
    b.sd(23, 0, 0x148)

    # Completion signal with dependencies on both store operands.
    b.addi(24, 0, TOHOST_ADDR)
    b.addi(25, 0, 1)
    b.sd(25, 24, 0)

    b.label("spin")
    b.jal(0, "spin")

    words = b.resolve()

    expected = {
        "ex_mem_forward": 15,
        "mem_wb_forward": 16,
        "ex_mem_priority": 17,
        "x0_guard": 10,
        "store_load": 0x45,
        "branch_taken": 42,
        "branch_wrong_path": 0,
        "jalr_target_value": 0x33,
        "jalr_wrong_path": 0,
        "lui_addi_value": 0x1234_5678,
        "jalr_link": b.labels["jalr_site"] + 4,
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
        "ex_mem_forward": read_u64(dmem, 0x100),
        "mem_wb_forward": read_u64(dmem, 0x108),
        "ex_mem_priority": read_u64(dmem, 0x110),
        "x0_guard": read_u64(dmem, 0x118),
        "store_value": read_u64(dmem, 0x120),
        "store_load": read_u64(dmem, 0x128),
        "branch_taken": read_u64(dmem, 0x130),
        "branch_wrong_path": read_u64(dmem, 0x158),
        "jalr_target_value": read_u64(dmem, 0x138),
        "jalr_link": read_u64(dmem, 0x140),
        "lui_addi_value": read_u64(dmem, 0x148),
        "jalr_wrong_path": read_u64(dmem, 0x150),
        "tohost": read_u64(dmem, TOHOST_ADDR),
    }
    assert observed["jalr_link"] == expected["jalr_link"], observed
    assert observed["ex_mem_forward"] == expected["ex_mem_forward"], observed
    assert observed["mem_wb_forward"] == expected["mem_wb_forward"], observed
    assert observed["ex_mem_priority"] == expected["ex_mem_priority"], observed
    assert observed["x0_guard"] == expected["x0_guard"], observed
    assert observed["branch_taken"] == expected["branch_taken"], observed
    assert observed["branch_wrong_path"] == expected["branch_wrong_path"], observed
    assert observed["store_value"] == 0x44, observed
    assert observed["store_load"] == expected["store_load"], observed
    assert observed["jalr_target_value"] == expected["jalr_target_value"], observed
    assert observed["jalr_wrong_path"] == expected["jalr_wrong_path"], observed
    assert observed["lui_addi_value"] == expected["lui_addi_value"], observed
    assert observed["tohost"] == 1, observed


@cocotb.test()
async def test_core_top_stage7_program(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    program_words, expected = build_stage7_program()
    dmem = await run_program(
        dut,
        program_words,
        max_cycles=4000,
        with_backpressure=False,
    )
    assert_program_results(dmem, expected)


@cocotb.test()
async def test_core_top_stage7_program_with_backpressure(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    program_words, expected = build_stage7_program()
    dmem = await run_program(
        dut,
        program_words,
        max_cycles=8000,
        with_backpressure=True,
    )
    assert_program_results(dmem, expected)
