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
