from __future__ import annotations

from dataclasses import dataclass

from cocotb.triggers import ClockCycles, ReadWrite, RisingEdge, Timer

from .elf_loader import ElfImage, elf_image_to_word_writes

MASK64 = (1 << 64) - 1


def _apply_store_to_u64(
    prev: int, addr: int, wdata: int, be: int, base_addr: int
) -> int:
    value = prev & MASK64
    word_base = addr & ~0x7
    for byte_idx in range(8):
        if ((be >> byte_idx) & 0x1) == 0:
            continue
        byte_addr = word_base + byte_idx
        if byte_addr < base_addr or byte_addr > (base_addr + 7):
            continue
        dst_shift = (byte_addr - base_addr) * 8
        src_shift = byte_idx * 8
        byte_val = (wdata >> src_shift) & 0xFF
        value &= ~(0xFF << dst_shift)
        value |= byte_val << dst_shift
    return value & MASK64


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
    wb_events: tuple[tuple[int, int, int], ...]
    retire_pcs: tuple[int, ...]
    retire_instrs: tuple[int, ...]
    store_events: tuple[tuple[int, int, int, int, int], ...]
    recent_if_pcs: tuple[int, ...]


async def run_until_termination(
    dut,
    *,
    max_cycles: int,
    tohost_addr: int = 0x200,
    expected_tohost: int | None = None,
    tohost_drain_cycles: int = 8,
    halt_repeat_cycles: int = 40,
    raise_on_timeout: bool = True,
    monitor_store_start: int | None = None,
    monitor_store_end: int | None = None,
    monitor_store_limit: int = 256,
) -> RunResult:
    wb_regs = [0] * 32
    wb_events: list[tuple[int, int, int]] = []
    retire_pcs: list[int] = []
    retire_instrs: list[int] = []
    store_events: list[tuple[int, int, int, int, int]] = []
    recent_if_pcs: list[int] = []

    last_if_pc = None
    repeated_if_pc = 0

    tohost_seen = False
    drain = 0
    tohost_shadow = await tb_read_u64(dut, tohost_addr)

    prev_wb_valid = 0
    prev_wb_rd = 0
    prev_wb_data = 0
    prev_retire_valid = 0
    prev_retire_pc = 0
    prev_retire_instr = 0

    for cycle in range(1, max_cycles + 1):
        await RisingEdge(dut.clk)
        await ReadWrite()

        if_pc = int(dut.dbg_if_pc.value) & MASK64
        recent_if_pcs.append(if_pc)
        if len(recent_if_pcs) > 32:
            recent_if_pcs.pop(0)

        if if_pc == last_if_pc:
            repeated_if_pc += 1
        else:
            repeated_if_pc = 1
            last_if_pc = if_pc

        wb_valid = int(dut.dbg_wb_valid.value)
        wb_rd = int(dut.dbg_wb_rd.value) & 0x1F
        wb_data = int(dut.dbg_wb_data.value) & MASK64
        retire_valid = int(dut.dbg_retire_valid.value)
        retire_pc = int(dut.dbg_retire_pc.value) & MASK64
        retire_instr = int(dut.dbg_retire_instr.value) & 0xFFFF_FFFF

        wb_event = wb_valid and (
            (not prev_wb_valid) or (wb_rd != prev_wb_rd) or (wb_data != prev_wb_data)
        )
        if wb_event and wb_rd != 0:
            wb_regs[wb_rd] = wb_data
            wb_events.append((wb_rd, wb_data, retire_pc))

        retire_event = retire_valid and (
            (not prev_retire_valid)
            or (retire_pc != prev_retire_pc)
            or (retire_instr != prev_retire_instr)
        )
        if retire_event:
            retire_pcs.append(retire_pc)
            retire_instrs.append(retire_instr)

        prev_wb_valid = wb_valid
        prev_wb_rd = wb_rd
        prev_wb_data = wb_data
        prev_retire_valid = retire_valid
        prev_retire_pc = retire_pc
        prev_retire_instr = retire_instr

        core_req = int(dut.u_core_top.dmem_req.value)
        core_we = int(dut.u_core_top.dmem_we.value)
        core_ready = int(dut.u_core_top.dmem_ready.value)
        if core_req and core_we and core_ready:
            addr = int(dut.u_core_top.dmem_addr.value) & MASK64
            wdata = int(dut.u_core_top.dmem_wdata.value) & MASK64
            be = int(dut.u_core_top.dmem_byte_en.value) & 0xFF

            if monitor_store_start is not None and monitor_store_end is not None:
                if monitor_store_start <= addr <= monitor_store_end:
                    if len(store_events) < monitor_store_limit:
                        pc = int(dut.u_core_top.mem_pc.value) & MASK64
                        store_events.append((cycle, pc, addr, wdata, be))

            if (addr <= (tohost_addr + 7)) and ((addr + 7) >= tohost_addr):
                tohost_shadow = _apply_store_to_u64(
                    tohost_shadow,
                    addr,
                    wdata,
                    be,
                    tohost_addr,
                )

        tohost_match = tohost_shadow != 0
        if expected_tohost is not None:
            tohost_match = tohost_shadow == (expected_tohost & MASK64)

        if tohost_match and not tohost_seen:
            tohost_seen = True
            drain = tohost_drain_cycles

        if tohost_seen:
            drain -= 1
            if drain <= 0:
                return RunResult(
                    reason="tohost",
                    cycles=cycle,
                    tohost=tohost_shadow,
                    wb_regs=tuple(wb_regs),
                    wb_events=tuple(wb_events),
                    retire_pcs=tuple(retire_pcs),
                    retire_instrs=tuple(retire_instrs),
                    store_events=tuple(store_events),
                    recent_if_pcs=tuple(recent_if_pcs),
                )

        if repeated_if_pc >= halt_repeat_cycles:
            return RunResult(
                reason="halt_loop",
                cycles=cycle,
                tohost=tohost_shadow,
                wb_regs=tuple(wb_regs),
                wb_events=tuple(wb_events),
                retire_pcs=tuple(retire_pcs),
                retire_instrs=tuple(retire_instrs),
                store_events=tuple(store_events),
                recent_if_pcs=tuple(recent_if_pcs),
            )

    if raise_on_timeout:
        raise AssertionError(
            "Program did not terminate before timeout"
            f"; recent_if_pcs={[hex(pc) for pc in recent_if_pcs]}"
        )

    tohost = await tb_read_u64(dut, tohost_addr)
    return RunResult(
        reason="timeout",
        cycles=max_cycles,
        tohost=tohost,
        wb_regs=tuple(wb_regs),
        wb_events=tuple(wb_events),
        retire_pcs=tuple(retire_pcs),
        retire_instrs=tuple(retire_instrs),
        store_events=tuple(store_events),
        recent_if_pcs=tuple(recent_if_pcs),
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
