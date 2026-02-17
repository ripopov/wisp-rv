import shutil
import subprocess
import tempfile
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadWrite, RisingEdge, Timer

MASK64 = (1 << 64) - 1
NOP = 0x00000013
TOHOST_ADDR = 0x200


def read_u64(memory: dict[int, int], addr: int) -> int:
    value = 0
    for i in range(8):
        value |= (memory.get(addr + i, 0) & 0xFF) << (8 * i)
    return value & MASK64


def write_u64(memory: dict[int, int], addr: int, wdata: int, byte_en: int) -> None:
    for i in range(8):
        if (byte_en >> i) & 1:
            memory[addr + i] = (wdata >> (8 * i)) & 0xFF


def require_toolchain() -> dict[str, str]:
    tools = {}
    for tool in (
        "riscv64-unknown-elf-gcc",
        "riscv64-unknown-elf-objcopy",
        "riscv64-unknown-elf-objdump",
    ):
        path = shutil.which(tool)
        if path is None:
            raise RuntimeError(f"Missing required toolchain binary: {tool}")
        tools[tool] = path
    return tools


def build_program() -> dict[int, int]:
    tools = require_toolchain()

    root = Path(__file__).resolve().parent
    src = root / "programs" / "stage6_smoke.S"
    linker = root / "linker.ld"

    with tempfile.TemporaryDirectory(prefix="wisp-rv64-stage6-") as tmpdir:
        out = Path(tmpdir)
        elf = out / "stage6_smoke.elf"
        bin_path = out / "stage6_smoke.bin"
        map_path = out / "stage6_smoke.map"
        dump_path = out / "stage6_smoke.dump"

        gcc_cmd = [
            tools["riscv64-unknown-elf-gcc"],
            "-march=rv64i",
            "-mabi=lp64",
            "-ffreestanding",
            "-nostdlib",
            "-nostartfiles",
            "-T",
            str(linker),
            f"-Wl,-Map,{map_path}",
            "-o",
            str(elf),
            str(src),
        ]
        subprocess.run(gcc_cmd, check=True, capture_output=True, text=True)

        objcopy_cmd = [
            tools["riscv64-unknown-elf-objcopy"],
            "-O",
            "binary",
            str(elf),
            str(bin_path),
        ]
        subprocess.run(objcopy_cmd, check=True, capture_output=True, text=True)

        objdump_cmd = [
            tools["riscv64-unknown-elf-objdump"],
            "-d",
            "-M",
            "no-aliases",
            str(elf),
        ]
        dump = subprocess.run(objdump_cmd, check=True, capture_output=True, text=True)
        dump_path.write_text(dump.stdout)

        data = bin_path.read_bytes()

    words: dict[int, int] = {}
    for idx in range(0, len(data), 4):
        chunk = data[idx : idx + 4]
        word = int.from_bytes(chunk.ljust(4, b"\x00"), "little")
        words[idx // 4] = word
    return words


async def reset_dut(dut, cycles: int = 5) -> None:
    dut.rst.value = 1
    dut.imem_ready.value = 1
    dut.imem_rdata.value = NOP
    dut.dmem_ready.value = 1
    dut.dmem_rdata.value = 0
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_stage6_program_end_to_end(dut):
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dut(dut)

    imem = build_program()
    dmem: dict[int, int] = {}

    tohost_seen = False
    drain_cycles = 0

    max_cycles = 10_000
    for cycle in range(max_cycles):
        await ReadWrite()

        imem_word_addr = (int(dut.imem_addr.value) & MASK64) >> 2
        dut.imem_ready.value = 1
        dut.imem_rdata.value = imem.get(imem_word_addr, NOP)

        if int(dut.dmem_req.value):
            dut.dmem_ready.value = 0 if (cycle % 5 == 2) else 1
        else:
            dut.dmem_ready.value = 1

        dmem_addr_aligned = (int(dut.dmem_addr.value) & MASK64) & ~0x7
        dut.dmem_rdata.value = read_u64(dmem, dmem_addr_aligned)

        await Timer(1, unit="ns")

        dmem_req = int(dut.dmem_req.value)
        dmem_we = int(dut.dmem_we.value)
        dmem_ready = int(dut.dmem_ready.value)

        if dmem_req and dmem_ready and dmem_we:
            addr_aligned = (int(dut.dmem_addr.value) & MASK64) & ~0x7
            wdata = int(dut.dmem_wdata.value) & MASK64
            byte_en = int(dut.dmem_byte_en.value) & 0xFF
            write_u64(dmem, addr_aligned, wdata, byte_en)

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
        raise AssertionError("Program did not complete before timeout")

    assert read_u64(dmem, TOHOST_ADDR) == 1
    assert read_u64(dmem, 0x100) == 15
    assert read_u64(dmem, 0x108) == 42
    assert read_u64(dmem, 0x110) == 0
    assert read_u64(dmem, 0x120) == 0x55
    assert read_u64(dmem, 0x128) == 0x56
    assert read_u64(dmem, 0x130) == 0x33
    assert read_u64(dmem, 0x138) != 0
    assert read_u64(dmem, 0x140) == 0x1234_5678
