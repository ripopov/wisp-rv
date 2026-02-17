# AGENTS

This document defines project goals and non-negotiable requirements for contributors and coding agents.

## Project goals

- Implement an RV64 RISC-V CPU core in SystemVerilog.
- Build high-confidence verification using Python and cocotb.
- Use Verilator as the default simulator for all local and CI runs.
- Grow from unit-level verification to full-system end-to-end RV64 program execution.

## Project requirements

- Each hardware unit must live under `units/<unit-name>/`.
- Each unit directory must include:
  - `rtl/` for SystemVerilog source
  - `tb/` for cocotb tests
  - `Makefile` for Verilator simulation entrypoint
- Every new unit must include at least one passing cocotb test before merge.
- Unit tests should include directed edge cases and randomized checks.
- Top-level CPU + memory subsystem tests must be placed in `tests/integration/` and run complete RV64 programs end-to-end.
- Integration tests must build RV64 programs from source with `riscv64-unknown-elf-gcc`; prebuilt ELF/BIN files are not the primary verification path.

## Toolchain requirements

- HDL: SystemVerilog
- Test framework: cocotb (Python)
- Simulator: Verilator
- Bare-metal compiler: RISC-V GNU toolchain with `riscv64-unknown-elf-*` binaries
- Python dependencies are defined in `requirements.txt`.

## Bare-metal compiler status (checked 2026-02-16)

- `riscv64-unknown-elf-gcc` found at `/opt/homebrew/bin/riscv64-unknown-elf-gcc`
- `riscv64-unknown-elf-gcc` version: `15.1.0`
- `riscv64-unknown-elf-objcopy` found at `/opt/homebrew/bin/riscv64-unknown-elf-objcopy`
- `riscv64-unknown-elf-objdump` found at `/opt/homebrew/bin/riscv64-unknown-elf-objdump`

## Bare-metal compiler usage

- Use ISA flags that match the implemented stage:
  - Pre-CSR stages: `-march=rv64i -mabi=lp64`
  - CSR-enabled stages: `-march=rv64i_zicsr -mabi=lp64`
  - M-extension stages: `-march=rv64im_zicsr -mabi=lp64`
- Build an ELF image for simulation:

```bash
riscv64-unknown-elf-gcc <isa-flags> -ffreestanding -nostdlib -nostartfiles \
  -T <linker-script.ld> -Wl,-Map,<program>.map -o <program>.elf <program>.S
```

- In automated tests, compile programs before simulation and fail fast if toolchain binaries are missing.

- Convert ELF to a flat binary image when needed by the memory model:

```bash
riscv64-unknown-elf-objcopy -O binary <program>.elf <program>.bin
```

- Generate disassembly for debug and retirement-trace correlation:

```bash
riscv64-unknown-elf-objdump -d -M no-aliases <program>.elf
```

## Development notes

- Keep test stimulus deterministic where possible (seed randomized tests).
- Prefer small, independently testable units before integration.
- Update `README.md` when structure, goals, or workflows change.

## Stage-06 lessons learned (keep applying)

- In cocotb memory-driver loops, synchronize with the DUT combinational outputs using `await ReadWrite()` before sampling `imem_addr`/`dmem_*` and driving memory responses. This avoids one-cycle skew bugs.
- Do not use `Timer(0)` as a delta-cycle sync in cocotb 2.x; it raises an error. Use `ReadWrite()` (or another explicit trigger) instead.
- Stage-06 core has no forwarding or hazard detection. Directed and integration programs must insert explicit NOP spacing between producer/consumer instruction pairs, especially ALU->use, load->use, and U-type/JALR setup sequences.
- For AUIPC/JALR tests, avoid brittle hard-coded offsets when possible. Prefer label/fixup-based immediate generation in Python-built programs; if using hand-written assembly, update offsets whenever instruction spacing changes.
- Branch/redirect tests should assert both sides of correctness: taken-path side effects must appear and wrong-path side effects must remain absent.
- Keep integration completion signaling deterministic: write `tohost`, then allow a short drain window so in-flight pipeline activity can retire before final memory assertions.
- Local test commands should include the project virtualenv on `PATH` so `cocotb-config` resolves, for example: `PATH="$(pwd)/.venv/bin:$PATH" make -C <target> SIM=verilator`.

## Stage-07 lessons learned (keep applying)

- Load-use hazard detection must be opcode-aware about source register usage. Do not treat IF/ID `rs2` bits as a true dependency for I-type ops (`OP_IMM`, `OP_IMM_32`, `LOAD`, `JALR`) or false stalls will appear.
- EX/MEM forwarding must not be used for loads (`mem_to_reg=1`) because load data is not available until MEM/WB. Only forward EX/MEM when the value is already final (for example ALU results).
- Store-data forwarding is required too: feed forwarded `rs2` into `ex_mem_reg.rs2_data_in`, otherwise `ALU -> SD` back-to-back sequences can store stale values.
- Keep control priority deterministic: redirect flush must override load-use stall requests so younger instructions are flushed, not held.
- For wrong-path checks, use isolated 8-byte-aligned marker addresses. Avoid nearby addresses that share one 64-bit word (for example `0x130` and `0x134`) to prevent readback alias confusion.
- The GNU assembler in this flow may reject label arithmetic directly in `addi` immediates. For hand-written assembly smoke tests, use explicit constants; for Python-built tests, prefer label/fixup generation.
- If a small unit test includes `rv64_pkg.sv` and uses `-Wall`, add `-Wno-UNUSEDPARAM` in that unit Makefile to avoid Verilator failing on intentionally unused package constants.

## Stage-08 lessons learned (keep applying)

- CSR instructions that produce `rd` values behave like load results for hazards: the produced value is only available at WB in this pipeline. Stall younger consumers of that `rd` for one cycle (similar to load-use handling).
- Trap-path tests must account for handler behavior, not just entry behavior. If the handler increments `mepc` before `mret`, expected post-trap `mepc` observations should match the resumed PC (for example trap site + 4).
- Keep trap-vector setup robust: use label-based address generation (`la` in assembly or label fixups in Python builders) instead of brittle hard-coded offsets.
- For illegal CSR writes, assert full trap payload correctness (`mcause=2`, `mepc` resume point, and `mtval` equal to the trapping instruction encoding), not only that a redirect occurred.
