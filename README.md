# wisp-rv64

RV64 RISC-V core project in SystemVerilog with unit tests in Python (cocotb) and simulation using Verilator.

## Repository layout

- `units/<unit-name>/rtl`: RTL implementation for a unit
- `units/<unit-name>/tb`: cocotb testbench for a unit
- `units/<unit-name>/Makefile`: simulation entrypoint for that unit
- `tests/integration`: top-level CPU + memory subsystem tests (to be expanded)

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
