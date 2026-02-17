# Integration tests

This directory is reserved for top-level cocotb testbenches that will run full RV64 programs end-to-end against the integrated CPU core and memory subsystem.

Current integration entrypoint:

- `Makefile` (Verilator + cocotb for `memory_subsystem`)
- `test_core_top_integration.py` (builds source program artifacts via `utils/build_rv64_program.py`, loads RAM, and runs end-to-end)
- `test_program_build.py` (toolchain/build-pipeline smoke for `.S` and `.c` programs)
- `programs/` (integration program sources)
- `linker/rv64.ld` (shared integration linker script)
- `utils/toolchain.py` (toolchain discovery + diagnostics)
- `utils/build_rv64_program.py` (compiler wrapper and artifact generation)

Run integration test:

```bash
PATH="$(pwd)/.venv/bin:$PATH" make -C tests/integration SIM=verilator
```

Run build-pipeline tests:

```bash
PATH="$(pwd)/.venv/bin:$PATH" pytest tests/integration/test_program_build.py
```
