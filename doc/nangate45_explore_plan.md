# Nangate45/OpenRAM FreePDK45 Exploration Target Plan (Updated with IO-Registered Benchmarks)

## Summary
Add a new optional flow target `//flow:explore_nangate45` that benchmarks a fixed logic suite plus a compact RAM geometry sweep on `nangate45` with OpenRAM `freepdk45`, runs pre-PnR STA, and generates a ranked max-frequency study report.
All benchmark units will be wrapped with input/output DFF stages so timing is measured as consistent reg-to-reg paths.

## Scope and Success Criteria
- New optional target only; existing canonical flow (`//:flow`) and CI required stages remain unchanged.
- Benchmark set: 4 logic circuits + 6 RAM geometries.
- Each benchmark measured with pre-PnR STA and binary-searched `fmax`.
- Study report includes per-design `fmax`, period at WNS ~= 0, WNS/TNS, and critical-path reference.
- Output artifacts under `reports/studies/nangate45_openram_freepdk45/`.

## Public Interfaces / Targets / Types Changes
- New Bazel target: `//flow:explore_nangate45`
- New flow runner stage: `stage_explore_nangate45`
- New report files:
  - `reports/studies/nangate45_openram_freepdk45/summary.md`
  - `reports/studies/nangate45_openram_freepdk45/summary.json`
- Per-design metadata schema (JSON fragment):
  - `design_name`, `category` (`logic|ram`), `top_module`
  - `clock_period_ns_at_wns_zero`, `fmax_mhz`, `wns_ns`, `tns_ns`
  - `status`, `error_message` (optional), `report_dir`

## Benchmark Matrix

### Logic Benchmarks (fixed suite)
1. `bench_add32_pipe`
2. `bench_mux8x32_pipe`
3. `bench_cmp64_pipe`
4. `bench_fifo_ctrl_small`

### RAM Geometries (compact 6-point sweep)
1. `8x64`
2. `16x64`
3. `32x64`
4. `32x128`
5. `64x128`
6. `128x256`

## IO DFF Wrapping Rule (Explicit)
Applies to every benchmark top included in exploration.

1. Input-side DFF stage:
- Register all functional inputs at the benchmark boundary on `clk`.
- Use explicit active-low reset behavior (`rst_n`) consistent with repo style.

2. Output-side DFF stage:
- Register all observable outputs before top-level output ports.

3. Timing objective:
- STA evaluates internal combinational logic between launch/capture flops.
- Reported `fmax` is reg-to-reg comparable across all designs.

4. RAM-specific requirement:
- Register `addr`, `csb`, `web`, `wmask`, `din` before macro interface.
- Register macro `dout` before top output.
- Macro remains black-box/lib-driven in synthesis/STA.

## Implementation Design

### 1) New sources and constraints
- Add logic benchmark RTL in `rtl/bench/`.
- Add matching SDC files in `constraints/bench/` with:
  - `create_clock` on `clk`
  - reset false-path
  - minimal IO delays (non-dominant due to IO flops)

### 2) OpenRAM matrix generation
- Add `scripts/gen_openram_cfg_matrix.py` to emit runtime cfg files for 6 geometries.
- Generate OpenRAM netlists/libs into `build/studies/openram/<macro>/`.

### 3) Synthesis per benchmark
- Logic: Yosys synth each benchmark top with Nangate45 liberty.
- RAM: auto-generate wrapper tops (with IO flops) in build dir per geometry, then synth with OpenRAM `.v` as macro libs.
- Write netlists to `build/studies/synth/<design>/<design>_synth.v`.

### 4) STA and fmax extraction
- Add `scripts/opensta_prenpr_study.tcl` parameterized by env vars.
- Use binary search on clock period:
  - initial bounds `0.2ns..10ns`, expand upper bound to `20ns` if needed
  - 18 iterations
  - pass criterion `WNS >= 0`
- Compute `fmax_mhz = 1000 / period_ns_at_wns_zero`.

### 5) Study report generation
- Add `scripts/generate_explore_report.py`.
- Aggregate per-design results and produce ranked markdown/json summaries.
- Include separate sections for logic vs RAM.

### 6) Flow/Bazel/docs wiring
- Update:
  - `flow/flow_runner.sh`
  - `flow/BUILD.bazel`
  - `rtl/BUILD.bazel`
  - `constraints/BUILD.bazel`
  - `scripts/BUILD.bazel`
  - `README.md`
  - `AGENTS.md` (new optional target + outputs)

## Test Cases and Scenarios

1. Syntax/static checks:
- `bash -n flow/flow_runner.sh`
- `python3 -m py_compile scripts/gen_openram_cfg_matrix.py scripts/generate_explore_report.py`

2. New target execution:
- `bazel run //flow:explore_nangate45`

3. Result validation:
- 10 benchmark entries present (4 logic + 6 RAM)
- each entry has status + `fmax` or explicit failure reason
- report ranking present and deterministic

4. Regression:
- `bazel run //flow:openram`
- `bazel run //flow:synth`
- `bazel run //flow:sta`
- confirm no behavior drift in existing flow outputs

## Assumptions and Defaults
- Corner fixed at TT/1.0V/25C.
- Exploration is optional, not required in CI.
- Generated artifacts remain untracked (`build/`, `reports/`).
- If any benchmark fails, overall stage exits non-zero after writing partial summary with failure details.
