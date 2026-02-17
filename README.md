# wisp-rv64

RV64 RISC-V core project in SystemVerilog with unit tests in Python (cocotb) and simulation using Verilator.

## Project goals

- Implement an RV64 RISC-V CPU core in SystemVerilog.
- Build reliable verification using Python + cocotb.
- Use Verilator as the default simulator for all verification runs.
- Progress from unit-level tests to full-system end-to-end RV64 program execution.

## Project requirements

- Each hardware unit lives in `units/<unit-name>/`.
- Each unit directory includes:
  - `rtl/` for SystemVerilog RTL
  - `tb/` for cocotb tests
  - `Makefile` for Verilator simulation entrypoint
- Every new unit must include at least one passing cocotb test.
- Unit tests should include both directed edge cases and randomized checks.
- Integration tests for CPU + memory subsystem live in `tests/integration/` and run complete RV64 programs end-to-end.

## Repository layout

- `units/<unit-name>/rtl`: RTL implementation for a unit
- `units/<unit-name>/tb`: cocotb testbench for a unit
- `units/<unit-name>/Makefile`: simulation entrypoint for that unit
- `tests/integration`: top-level CPU + memory subsystem end-to-end tests

## First implemented unit: ALU

- RTL: `units/alu/rtl/alu.sv`
- Testbench: `units/alu/tb/test_alu.py`

Setup Python dependencies (Python 3.13+):

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run the ALU test:

```bash
PATH="$(pwd)/.venv/bin:$PATH" make -C units/alu SIM=verilator
```
