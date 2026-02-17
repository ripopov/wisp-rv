from __future__ import annotations

from dataclasses import dataclass

from cocotb.triggers import ClockCycles, RisingEdge, Timer

from .elf_loader import ElfImage, elf_image_to_word_writes

MASK64 = (1 << 64) - 1


def init_tb_ports(dut) -> None:
    dut.tb_mem_wr_en.value = 0
    dut.tb_mem_is_data.value = 1
    dut.tb_mem_wr_addr.value = 0
    dut.tb_mem_wr_data.value = 0
    dut.tb_mem_wr_be.value = 0
    dut.tb_mem_rd_addr.value = 0


async def tb_write_word(
    dut,
    word_idx: int,
    value: int,
    be: int = 0xFF,
    *,
    is_data: bool = True,
) -> None:
    dut.tb_mem_is_data.value = 1 if is_data else 0
    dut.tb_mem_wr_addr.value = (word_idx << 3) & MASK64
    dut.tb_mem_wr_data.value = value & MASK64
    dut.tb_mem_wr_be.value = be & 0xFF
    dut.tb_mem_wr_en.value = 1
    await RisingEdge(dut.clk)
    dut.tb_mem_wr_en.value = 0


async def tb_read_word(dut, word_idx: int, *, is_data: bool = True) -> int:
    dut.tb_mem_is_data.value = 1 if is_data else 0
    dut.tb_mem_rd_addr.value = (word_idx << 3) & MASK64
    await Timer(1, unit="ns")
    return int(dut.tb_mem_rd_data.value) & MASK64


async def tb_read_u64(dut, addr: int, *, is_data: bool = True) -> int:
    assert (addr & 0x7) == 0
    return await tb_read_word(dut, addr >> 3, is_data=is_data)


async def clear_ram_prefix(dut, words: int = 1024) -> None:
    for idx in range(words):
        await tb_write_word(dut, idx, 0, 0xFF, is_data=False)
        await tb_write_word(dut, idx, 0, 0xFF, is_data=True)


async def load_elf_image_to_ram(
    dut,
    image: ElfImage,
    *,
    clear_words: int = 1024,
    load_imem: bool = True,
    load_dmem: bool = True,
) -> None:
    await clear_ram_prefix(dut, words=clear_words)

    writes = elf_image_to_word_writes(image)
    for word_addr in sorted(writes):
        word_data, word_be = writes[word_addr]
        word_idx = word_addr >> 3
        if load_imem:
            await tb_write_word(dut, word_idx, word_data, word_be, is_data=False)
        if load_dmem:
            await tb_write_word(dut, word_idx, word_data, word_be, is_data=True)


@dataclass(frozen=True)
class RunResult:
    reason: str
    cycles: int
    tohost: int
    wb_regs: tuple[int, ...]
    retire_pcs: tuple[int, ...]
    recent_if_pcs: tuple[int, ...]


async def run_until_termination(
    dut,
    *,
    max_cycles: int,
    tohost_addr: int = 0x200,
    tohost_drain_cycles: int = 8,
    halt_repeat_cycles: int = 40,
) -> RunResult:
    wb_regs = [0] * 32
    retire_pcs: list[int] = []
    recent_if_pcs: list[int] = []

    last_if_pc = None
    repeated_if_pc = 0

    tohost_seen = False
    drain = 0

    for cycle in range(1, max_cycles + 1):
        await RisingEdge(dut.clk)

        if_pc = int(dut.dbg_if_pc.value) & MASK64
        recent_if_pcs.append(if_pc)
        if len(recent_if_pcs) > 32:
            recent_if_pcs.pop(0)

        if if_pc == last_if_pc:
            repeated_if_pc += 1
        else:
            repeated_if_pc = 1
            last_if_pc = if_pc

        if int(dut.dbg_wb_valid.value):
            rd = int(dut.dbg_wb_rd.value) & 0x1F
            if rd != 0:
                wb_regs[rd] = int(dut.dbg_wb_data.value) & MASK64

        if int(dut.dbg_retire_valid.value):
            retire_pcs.append(int(dut.dbg_retire_pc.value) & MASK64)

        tohost = await tb_read_u64(dut, tohost_addr)
        if tohost != 0 and not tohost_seen:
            tohost_seen = True
            drain = tohost_drain_cycles

        if tohost_seen:
            drain -= 1
            if drain <= 0:
                return RunResult(
                    reason="tohost",
                    cycles=cycle,
                    tohost=tohost,
                    wb_regs=tuple(wb_regs),
                    retire_pcs=tuple(retire_pcs),
                    recent_if_pcs=tuple(recent_if_pcs),
                )

        if repeated_if_pc >= halt_repeat_cycles:
            return RunResult(
                reason="halt_loop",
                cycles=cycle,
                tohost=tohost,
                wb_regs=tuple(wb_regs),
                retire_pcs=tuple(retire_pcs),
                recent_if_pcs=tuple(recent_if_pcs),
            )

    raise AssertionError(
        "Program did not terminate before timeout"
        f"; recent_if_pcs={[hex(pc) for pc in recent_if_pcs]}"
    )


async def reset_and_load_elf(
    dut,
    image: ElfImage,
    *,
    reset_cycles: int = 2,
    clear_words: int = 1024,
    load_imem: bool = True,
    load_dmem: bool = True,
) -> None:
    dut.rst.value = 1
    await ClockCycles(dut.clk, reset_cycles)
    await load_elf_image_to_ram(
        dut,
        image,
        clear_words=clear_words,
        load_imem=load_imem,
        load_dmem=load_dmem,
    )
    await ClockCycles(dut.clk, reset_cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
