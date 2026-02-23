# mem-comp experiments

This repository contains a small memory-comparison flow that:

- builds a reproducible devcontainer for open-source EDA,
- implements a simple 2-way set-associative cache in SystemVerilog,
- generates cache SRAM macros with OpenRAM (FreePDK45 tech, netlist-only mode),
- synthesizes on Nangate45 with Yosys,
- and runs pre-PnR timing in OpenSTA.

## Project layout

- `.devcontainer/`: devcontainer definition and Dockerfile
- `rtl/`: cache RTL and SRAM wrappers
- `tb/`: behavioral testbench
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

Open in VS Code and rebuild container, then run:

```bash
make flow
```

`scripts/setup_tools.sh` clones the pinned tool sources into `.tools/`:

- OpenRAM `v1.2.48`
- OpenROAD-flow-scripts (sparse checkout of `flow/platforms/nangate45`)

## Running the flow

Run each stage individually:

```bash
make setup
make openram
make sim
make synth
make sta
```

Or run all at once:

```bash
make flow
```

Artifacts:

- OpenRAM outputs: `build/openram/`
- Synthesized netlist: `build/synth/set_assoc_cache_2way_synth.v`
- OpenSTA pre-PnR reports: `reports/sta/`

## Notes

- OpenRAM is configured in netlist-only mode to keep the flow lightweight and deterministic.
- The behavioral simulation uses an SRAM model compatible with OpenRAM 1RW timing style.
- Synthesis and STA use Nangate45 liberty from OpenROAD-flow-scripts.
