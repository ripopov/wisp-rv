# ooo-cpu experiments

This repository tracks incremental milestones toward an out-of-order RISC-V core.

Current milestone in this repo:

- builds a reproducible devcontainer for open-source EDA,
- implements a simple 2-way set-associative cache in SystemVerilog,
- verifies cache behavior with a SystemC testbench on Verilator,
- builds and runs a bare-metal RV64 C smoke test on Spike,
- generates cache SRAM macros with OpenRAM (FreePDK45 tech, netlist-only mode),
- synthesizes on Nangate45 with Yosys,
- and runs pre-PnR timing in OpenSTA.

## Long-term goal

- Build a complete out-of-order RISC-V CPU core.
- Get there in small, validated steps (memory subsystem, pipelines, scheduling, execution, and integration).

## Project layout

- `.devcontainer/`: devcontainer definition and Dockerfile
- `rtl/`: cache RTL and SRAM wrappers
- `tb/`: SystemC behavioral testbench
- `sw/`: bare-metal RISC-V software examples
- `openram/`: OpenRAM macro config files
- `constraints/`: SDC constraints for pre-PnR timing
- `scripts/`: setup and flow scripts

## Cache microarchitecture

- 2-way set-associative cache
- 64 sets
- 1 word (32-bit) per line
- write-allocate, write-hit update with byte mask
- no external refill path yet; read miss returns miss with zero data
- data and tag arrays implemented as SRAM instances

SRAM macro targets:

- `sram_data_32x64_1rw`
- `sram_tag_24x64_1rw`

## Devcontainer

The devcontainer uses `hpretl/iic-osic-tools` as base and adds a stable CLI-friendly entrypoint.
It pre-installs pinned OpenRAM/ORFS/SystemC tool sources under `/opt/wisp-tools`
and sets `OPENRAM_ROOT`, `ORFS_ROOT`, and `SYSTEMC_ROOT` in container env, so
manual `make setup` is not required for normal devcontainer use.

Open in VS Code and rebuild container, then run:

```bash
make flow
```

Pinned tool versions:

- OpenRAM `v1.2.48`
- OpenROAD-flow-scripts (sparse checkout of `flow/platforms/nangate45`)
- SystemC `3.0.2`

It also verifies that these tools are available in PATH:

- `verilator`
- `spike` (riscv-isa-sim)
- `riscv64-unknown-elf-gcc` (bare-metal cross compiler)

`make setup` remains available as a fallback bootstrap for non-devcontainer
environments.

## Running the flow

Run each stage individually:

```bash
make setup
make openram
make sim
make spike
make synth
make sta
```

Or run all at once:

```bash
make flow
```

`make flow` executes stages serially via `scripts/run_all.sh` to avoid accidental
stage fanout under `make -j`.

Heavy compile steps are capped by default:

- `FLOW_JOBS=min(host_cores, 4)`
- `SYSTEMC_BUILD_JOBS=${FLOW_JOBS}` for `make setup`
- `VERILATOR_JOBS=${FLOW_JOBS}` for `make sim`

Override locally when needed:

```bash
FLOW_JOBS=2 make flow
SYSTEMC_BUILD_JOBS=2 make setup
VERILATOR_JOBS=2 make sim
```

Artifacts:

- OpenRAM outputs: `build/openram/`
- Simulation executable: `build/sim/obj_dir/tb_set_assoc_cache_sim`
- Spike bare-metal ELF: `build/spike/basic.elf`
- Synthesized netlist: `build/synth/set_assoc_cache_2way_synth.v`
- OpenSTA pre-PnR reports: `reports/sta/`

## Simulation test

`make sim` compiles and runs `tb/tb_set_assoc_cache.cpp` using Verilator's
SystemC flow (`--sc`).

To run the SystemC test directly:

```bash
source scripts/env.sh
export LD_LIBRARY_PATH="${SYSTEMC_LIBDIR}:${LD_LIBRARY_PATH:-}"
verilator --sc --timing --build -j "${VERILATOR_JOBS}" -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL \
  --Mdir build/sim/obj_dir \
  --top-module set_assoc_cache_2way \
  --exe tb/tb_set_assoc_cache.cpp \
  -o tb_set_assoc_cache_sim \
  rtl/cache_sram_1rw.sv rtl/set_assoc_cache_2way.sv
build/sim/obj_dir/tb_set_assoc_cache_sim
```

## Spike bare-metal example

The repository includes a minimal freestanding RV64 example in `sw/basic/`.

Build and run it under Spike:

```bash
make spike
```

This compiles the ELF with `riscv64-unknown-elf-gcc` and executes it with
`spike --isa=rv64imac`.

## GitHub Actions CI

Workflow: `.github/workflows/eda-ci.yml`

On each push, pull request, or manual dispatch, CI runs:

- setup + tool bootstrap,
- OpenRAM macro generation,
- simulation tests,
- Spike bare-metal smoke test,
- synthesis,
- and pre-PnR STA.

CI publishes a markdown + JSON summary at `reports/ci/` and includes:

- test status,
- synthesis gate count,
- STA WNS/TNS,
- implied max clock frequency,
- and the max critical-path report excerpt.

## Notes

- OpenRAM is configured in netlist-only mode to keep the flow lightweight and deterministic.
- The Verilator + SystemC simulation uses an SRAM model compatible with OpenRAM 1RW timing style.
- Synthesis and STA use Nangate45 liberty from OpenROAD-flow-scripts.
