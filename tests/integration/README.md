# Integration tests

This directory is reserved for top-level cocotb testbenches that will run full RV64 programs end-to-end against the integrated CPU core and memory subsystem.

Current integration entrypoint:

- `Makefile` (Verilator + cocotb for `memory_subsystem`)
- `test_core_top_integration.py` (builds source program artifacts via `utils/build_rv64_program.py`, loads RAM, and runs end-to-end)
- `test_program_build.py` (toolchain/build-pipeline smoke for `.S` and `.c` programs)
- `test_rv64_programs.py` (curated end-to-end RV64 suite with cycle budgets and retire-trace/disassembly checks)
- `test_randomized_streams.py` (deterministic randomized ALU streams validated against a software reference model)
- `programs/` (integration program sources)
- `linker/rv64.ld` (shared integration linker script)
- `utils/toolchain.py` (toolchain discovery + diagnostics)
- `utils/build_rv64_program.py` (compiler wrapper and artifact generation)
- `utils/elf_loader.py` (ELF PT_LOAD parsing and address-aware memory image generation)
- `utils/reference_model.py` (software RV64 reference model used by randomized integration checks)
- `utils/sim_harness.py` (shared cocotb memory-subsystem load/run helpers)

Run integration test:

```bash
PATH="$(pwd)/.venv/bin:$PATH" make -C tests/integration SIM=verilator
```

Run build-pipeline tests:

```bash
PATH="$(pwd)/.venv/bin:$PATH" pytest tests/integration/test_program_build.py
```

Optional randomized-stream controls:

- `WISP_RAND_SEED` (default `0x5A170001`)
- `WISP_RAND_CASES` (default `3`)
- `WISP_RAND_OPS` (default `160`)
