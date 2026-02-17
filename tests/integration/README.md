# Integration tests

This directory is reserved for top-level cocotb testbenches that will run full RV64 programs end-to-end against the integrated CPU core and memory subsystem.

Current integration entrypoint:

- `Makefile` (Verilator + cocotb for `core_top`)
- `test_core_top_integration.py` (builds assembly program with `riscv64-unknown-elf-gcc` and runs end-to-end)
- `programs/stage9_smoke.S` (Stage-09 CSR/trap/M-extension smoke program)

Run integration test:

```bash
PATH="$(pwd)/.venv/bin:$PATH" make -C tests/integration SIM=verilator
```
