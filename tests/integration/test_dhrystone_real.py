from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import cocotb
from cocotb.clock import Clock

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from utils.build_rv64_program import DEFAULT_MABI, DEFAULT_MARCH, build_rv64_program
from utils.elf_loader import load_elf_image
from utils.sim_harness import (
    init_tb_ports,
    reset_and_load_elf,
    run_until_termination,
    tb_read_u64,
)

DHRY_ITERS = 200
TOHOST_ADDR = 0x7000
TOHOST_DONE_MAGIC = 0xD15EA5E1
RESULT_BASE = 0x7040


@cocotb.test()
async def test_dhrystone_real_v21(dut):
    init_tb_ports(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    with tempfile.TemporaryDirectory(prefix="wisp-rv64-dhrystone-real-") as tmpdir:
        artifacts = build_rv64_program(
            source=THIS_DIR / "benchmarks" / "dhrystone_real_port.c",
            linker_script=THIS_DIR / "linker" / "rv64_32k.ld",
            output_dir=Path(tmpdir),
            march=DEFAULT_MARCH,
            mabi=DEFAULT_MABI,
            extra_gcc_flags=(
                "-O2",
                "-std=gnu89",
                "-DTIME",
                f"-DDHRY_ITERS={DHRY_ITERS}",
                "-fno-builtin-printf",
                "-fno-builtin-scanf",
                "-fno-builtin-malloc",
                "-fno-builtin-strcpy",
                "-fno-builtin-strcmp",
            ),
        )

        image = load_elf_image(artifacts.elf_path)
        await reset_and_load_elf(
            dut,
            image,
            reset_cycles=2,
            clear_words=4096,
            load_imem=True,
            load_dmem=True,
        )

        run = await run_until_termination(
            dut,
            max_cycles=2_000_000,
            tohost_addr=TOHOST_ADDR,
            expected_tohost=TOHOST_DONE_MAGIC,
            tohost_drain_cycles=8,
            halt_repeat_cycles=512,
            raise_on_timeout=False,
        )

        if run.reason != "tohost":
            raise AssertionError(
                "Dhrystone did not terminate: "
                f"reason={run.reason} cycles={run.cycles} "
                f"tohost=0x{run.tohost:x} "
                f"recent_if_pcs={[hex(pc) for pc in run.recent_if_pcs]}"
            )

        assert run.tohost == TOHOST_DONE_MAGIC, f"tohost mismatch ({run.tohost:#x})"

        int_glob = await tb_read_u64(dut, RESULT_BASE + 0x00)
        bool_glob = await tb_read_u64(dut, RESULT_BASE + 0x08)
        ch1 = await tb_read_u64(dut, RESULT_BASE + 0x10)
        ch2 = await tb_read_u64(dut, RESULT_BASE + 0x18)
        arr1_8 = await tb_read_u64(dut, RESULT_BASE + 0x20)
        arr2_8_7 = await tb_read_u64(dut, RESULT_BASE + 0x28)

        dut._log.info(
            "Dhrystone result words: int=%d bool=%d ch1=%d ch2=%d arr1_8=%d arr2_8_7=%d cycles=%d retired=%d",
            int_glob,
            bool_glob,
            ch1,
            ch2,
            arr1_8,
            arr2_8_7,
            run.cycles,
            len(run.retire_pcs),
        )
        assert int_glob == 5
        assert bool_glob == 1
        assert ch1 == ord("A")
        assert ch2 == ord("B")
        assert arr1_8 == 7
        assert arr2_8_7 == (DHRY_ITERS + 10)

        retired = len(run.retire_pcs)
        assert retired > 0

        cpi = run.cycles / float(retired)
        dut._log.info(
            "Dhrystone v2.1 complete: cycles=%d retired=%d CPI=%.4f",
            run.cycles,
            retired,
            cpi,
        )
