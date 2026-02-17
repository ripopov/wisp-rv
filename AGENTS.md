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

## Toolchain requirements

- HDL: SystemVerilog
- Test framework: cocotb (Python)
- Simulator: Verilator
- Python dependencies are defined in `requirements.txt`.

## Development notes

- Keep test stimulus deterministic where possible (seed randomized tests).
- Prefer small, independently testable units before integration.
- Update `README.md` when structure, goals, or workflows change.
