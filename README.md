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
- `flow/`: Bazel stage runners
- `scripts/`: STA TCL + CI report utility

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
and sets `OPENRAM_ROOT`, `ORFS_ROOT`, and `SYSTEMC_ROOT` in container env.
It also installs Bazelisk as `bazel` and uses `.bazelversion` to pin Bazel.

Open in VS Code and rebuild container, then run:

```bash
bazel run //:flow
```

Pinned tool versions:

- OpenRAM `v1.2.48`
- OpenROAD-flow-scripts (sparse checkout of `flow/platforms/nangate45`)
- SystemC `3.0.2`

It also verifies that these tools are available in PATH:

- `bazel`
- `verilator`
- `spike` (riscv-isa-sim)
- `riscv64-unknown-elf-gcc` (bare-metal cross compiler)

## Running the flow

Run each stage individually:

```bash
bazel run //flow:openram
bazel run //flow:sim
bazel run //flow:spike
bazel run //flow:synth
bazel run //flow:sta
bazel run //flow:explore_nangate45
```

Or run all at once:

```bash
bazel run //:flow
```

`//:flow` aliases `//flow:all` and executes stages serially (`openram -> sim -> spike -> synth -> sta`).
Clean generated flow artifacts with `bazel run //flow:clean`.

`//flow:explore_nangate45` is an optional study target. It sweeps a fixed logic
benchmark suite plus OpenRAM geometries on Nangate45 and generates a frequency
ranking report under `reports/studies/nangate45_openram_freepdk45/`.

Heavy compile steps are capped by default in `flow/flow_runner.sh`:

- `FLOW_JOBS=min(host_cores, 4)`
- `VERILATOR_JOBS=${FLOW_JOBS}` for `bazel run //flow:sim`
- `MAX_PARALLEL_JOBS=4` hard cap (including pre-set env vars)

Override locally when needed:

```bash
FLOW_JOBS=2 bazel run //:flow
VERILATOR_JOBS=2 bazel run //flow:sim
MAX_PARALLEL_JOBS=2 bazel run //flow:sim
```

Note: this project intentionally uses `WISP_VERILATOR_CMD` (not `VERILATOR_BIN`)
to avoid conflicting with Verilator wrapper internals.

Artifacts:

- OpenRAM outputs: `build/openram/`
- Simulation executable: `build/sim/obj_dir/tb_set_assoc_cache_sim`
- Spike bare-metal ELF: `build/spike/basic.elf`
- Synthesized netlist: `build/synth/set_assoc_cache_2way_synth.v`
- OpenSTA pre-PnR reports: `reports/sta/`
- Exploration study reports: `reports/studies/nangate45_openram_freepdk45/`

## Simulation test

`bazel run //flow:sim` compiles and runs `tb/tb_set_assoc_cache.cpp` using Verilator's
SystemC flow (`--sc`).

To run the SystemC test directly:

```bash
SYSTEMC_ROOT="${SYSTEMC_ROOT:-/opt/wisp-tools/systemc}"
SYSTEMC_LIBDIR="${SYSTEMC_LIBDIR:-${SYSTEMC_ROOT}/install/lib}"
if [ ! -f "${SYSTEMC_LIBDIR}/libsystemc.so" ] && [ -d "${SYSTEMC_ROOT}/install/lib64" ]; then
  SYSTEMC_LIBDIR="${SYSTEMC_ROOT}/install/lib64"
fi
export LD_LIBRARY_PATH="${SYSTEMC_LIBDIR}:${LD_LIBRARY_PATH:-}"
verilator --sc --timing --build -j 1 -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL \
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
bazel run //flow:spike
```

This compiles the ELF with `riscv64-unknown-elf-gcc` and executes it with
`spike --isa=rv64imac`.

## GitHub Actions CI

Workflow: `.github/workflows/eda-ci.yml`

On each push, pull request, or manual dispatch, CI runs:

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

## CI Reproduction (Local Docker)

Use the same container and uid/gid mapping as CI:

```bash
docker build -t wisp-eda-tools:ci -f .devcontainer/Dockerfile .
docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:openram"
docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:sim"
docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:spike"
docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:synth"
docker run --rm --user "$(id -u):$(id -g)" -e USER=ci -e HOME=/tmp -v "$PWD:/work" -w /work wisp-eda-tools:ci bash -lc "bazel run //flow:sta"
```

## Notes

- OpenRAM is configured in netlist-only mode to keep the flow lightweight and deterministic.
- The Verilator + SystemC simulation uses an SRAM model compatible with OpenRAM 1RW timing style.
- Synthesis and STA use Nangate45 liberty from OpenROAD-flow-scripts.
