# AGENTS.md

Guidance for agentic coding tools in this repository.
Project focus: incremental milestones toward an out-of-order RISC-V core.
Current milestone: cache + OpenRAM + Spike bare-metal smoke test + synth + pre-PnR STA flow.

## Scope And Priorities
- Keep the existing EDA flow working end-to-end.
- Prefer small, reviewable changes over broad refactors.
- Preserve reproducibility in devcontainer and CI.
- Do not commit generated outputs from `build/`, `reports/`, or `.tools/`.

## Repository Layout
- `rtl/`: synthesizable SystemVerilog.
- `tb/`: SystemC testbenches for Verilator simulation.
- `sw/`: bare-metal RISC-V software examples.
- `openram/`: OpenRAM SRAM configuration files.
- `constraints/`: SDC constraints for timing.
- `flow/`: Bazel stage runners.
- `scripts/`: utilities (`opensta_prenpr.tcl`, `generate_ci_report.py`).
- `.github/workflows/eda-ci.yml`: canonical CI execution.
- `.devcontainer/`: recommended local environment.

## Environment
- Base container: `hpretl/iic-osic-tools:latest`.
- Devcontainer pre-installs tool sources under `/opt/wisp-tools` and exports:
  - `OPENRAM_ROOT=/opt/wisp-tools/OpenRAM`
  - `ORFS_ROOT=/opt/wisp-tools/OpenROAD-flow-scripts`
  - `SYSTEMC_ROOT=/opt/wisp-tools/systemc`
- Devcontainer installs Bazelisk as `bazel` and pins Bazel via `.bazelversion`.
- Tool bootstrap clones:
  - OpenRAM `v1.2.48`
  - OpenROAD-flow-scripts (sparse checkout for Nangate45)
  - SystemC `3.0.2`

## Canonical Build/Test Commands
Run from repository root.

- Full flow: `bazel run //flow:all`
- Stage-by-stage:
  - `bazel run //flow:openram`
  - `bazel run //flow:sim`
  - `bazel run //flow:spike`
  - `bazel run //flow:synth`
  - `bazel run //flow:sta`
- Clean generated outputs: `bazel run //flow:clean`
- Concurrency controls (defaults are capped to reduce local OOM risk):
  - `FLOW_JOBS` (global cap, defaults to `min(host_cores, 4)`)
  - `VERILATOR_JOBS` (defaults to `FLOW_JOBS`)
  - `MAX_PARALLEL_JOBS` (defaults to `4`)

## Running A Single Test (Important)
Current repo has one behavioral testbench: `tb/tb_set_assoc_cache.cpp`.

- Default: `bazel run //flow:sim`
- Direct single-test build/run:
  - `export SYSTEMC_ROOT="${SYSTEMC_ROOT:-/opt/wisp-tools/systemc}"`
  - `export SYSTEMC_LIBDIR="${SYSTEMC_LIBDIR:-${SYSTEMC_ROOT}/install/lib}"`
  - `if [ ! -f "${SYSTEMC_LIBDIR}/libsystemc.so" ] && [ -d "${SYSTEMC_ROOT}/install/lib64" ]; then export SYSTEMC_LIBDIR="${SYSTEMC_ROOT}/install/lib64"; fi`
  - `export LD_LIBRARY_PATH="${SYSTEMC_LIBDIR}:${LD_LIBRARY_PATH:-}"`
  - `verilator --sc --timing --build -j 1 -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL --Mdir build/sim/obj_dir --top-module set_assoc_cache_2way --exe tb/tb_set_assoc_cache.cpp -o tb_set_assoc_cache_sim rtl/cache_sram_1rw.sv rtl/set_assoc_cache_2way.sv`
  - `build/sim/obj_dir/tb_set_assoc_cache_sim`

If more tests are added, keep single-test invocation explicit and top-based.

## Running Spike Bare-Metal Example
- Default: `bazel run //flow:spike`
- Direct compile/run:
  - `riscv64-unknown-elf-gcc -march=rv64imac -mabi=lp64 -mcmodel=medany -msmall-data-limit=0 -nostdlib -nostartfiles -ffreestanding -Wl,-T,sw/basic/linker.ld -Wl,--no-warn-rwx-segments -Wl,--build-id=none sw/basic/start.S sw/basic/main.c -o build/spike/basic.elf`
  - `spike --isa=rv64imac build/spike/basic.elf`

## Lint / Static Checks
No dedicated lint target exists yet. Use ad hoc checks:

- Verilator lint:
  - `verilator --lint-only -Wall rtl/cache_sram_1rw.sv rtl/set_assoc_cache_2way.sv`
- Python syntax check:
  - `python3 -m py_compile scripts/generate_ci_report.py`
- Shell syntax check:
  - `bash -n flow/*.sh`

## CI Reproduction (Local Docker)
Use the same container and uid/gid mapping as CI:

- `docker build -t wisp-eda-tools:ci -f .devcontainer/Dockerfile .`
- `docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:openram"`
- `docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:sim"`
- `docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:spike"`
- `docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:synth"`
- `docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:sta"`

## Expected Outputs
- OpenRAM artifacts: `build/openram/`
- Simulation executable: `build/sim/obj_dir/tb_set_assoc_cache_sim`
- Spike artifact: `build/spike/basic.elf`
- Synth netlist: `build/synth/set_assoc_cache_2way_synth.v`
- STA reports: `reports/sta/`
- CI summary: `reports/ci/summary.md`, `reports/ci/summary.json`

## SystemVerilog Style Guidelines
- Use `logic` (avoid legacy `reg/wire` unless required).
- Prefer `always_ff` and `always_comb`.
- Use non-blocking assignments in sequential logic.
- In combinational blocks, assign defaults first to avoid latches.
- Keep parameter names `UPPER_SNAKE_CASE`.
- Keep module/file names `snake_case`.
- Use `_q` suffix for registered state.
- Name FSM states as `S_*` enums.
- Keep widths explicit; use `'0` for width-safe zeroing.
- Keep reset behavior explicit; current convention is active-low `rst_n`.
- Keep OpenRAM wrapper ports aligned with macro names (`clk0/csb0/web0/...`).

## Testbench Style Guidelines
- Use deterministic cycle stepping (`sc_start`) and avoid wall-clock sleeps.
- Keep helpers for request/response handshakes small and explicit.
- Fail fast with clear stderr messages and non-zero exit status.
- Print an explicit PASS marker at end of a successful run.
- Keep tests deterministic; avoid unseeded random behavior.

## Bash Style Guidelines
- Start scripts with:
  - `#!/usr/bin/env bash`
  - `set -euo pipefail`
- Keep flow environment resolution explicit inside each script.
- Quote variable expansions (`"${VAR}"`).
- Use `printf` (especially for errors/status).
- Validate required files/tools early and fail fast.
- Keep scripts rerunnable and idempotent where possible.

## Python Style Guidelines
- Use Python 3 stdlib by default.
- Prefer `pathlib.Path` for file handling.
- Keep imports clean and grouped (stdlib only today).
- Use type hints where they improve clarity.
- Use `argparse` for CLI behavior.
- Use `if __name__ == "__main__":` guard.
- Handle missing report inputs gracefully (`N/A`/fallback output).

## SDC/TCL Style Guidelines
- Keep constraints and STA scripts concise and deterministic.
- Use OpenSTA-compatible commands only.
- Keep report filenames stable under `reports/sta/`.

## Naming Conventions Summary
- Modules/files: `snake_case`
- Parameters/localparams: `UPPER_SNAKE_CASE`
- Registered signals: `*_q`
- FSM states: `S_*`
- SRAM macros: `sram_<type>_<width>x<depth>_1rw`

## Error Handling Expectations
- Scripts: explicit checks + clear stderr + non-zero exit.
- Testbenches: fail fast on first mismatch.
- CI: collect stage outcomes, but fail workflow if any required stage fails.

## Adding New Tests
- Prefer one top-level testbench per file under `tb/`.
- Keep compile/run commands explicit and scriptable.
- Update this file and README when test entry points change.
- Ensure CI still reports clear pass/fail status per stage.

## Agent Change Checklist
Before finalizing any change:

1. Run the narrowest relevant check first (single test/lint).
2. Run all affected flow stages.
3. Update docs when commands/behavior change.
4. Avoid unnecessary formatting churn.
5. Keep generated artifacts out of commits.

## Cursor / Copilot Rules
No repository-specific Cursor/Copilot instruction files were found:

- `.cursor/rules/`: not present
- `.cursorrules`: not present
- `.github/copilot-instructions.md`: not present

If these files are added later, treat them as higher-priority instructions and
update this AGENTS.md summary accordingly.
