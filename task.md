# Task Handoff (SystemC + Verilator Migration)

## Requested Task
Convert cache simulation from **SystemVerilog TB + Icarus** to **SystemC TB + Verilator**, remove Icarus from the flow, and verify end-to-end in container/CI. If needed, update devcontainer and GitHub CI for latest SystemC.

## Current Status
- Migration is partially implemented in code, but **simulation is still failing in container** during Verilator build step.
- Failure mode: `make sim` exits with **Error 137** (`Killed`), i.e. process receives signal 9 while running Verilator/SystemC build.
- Added a concurrency mitigation patch to reduce startup CPU/memory pressure:
  - `make flow` now runs serially through `scripts/run_all.sh` (no stage fanout under `make -j`).
  - Job defaults are now capped to `min(host_cores, 4)` via `scripts/env.sh` and reused by setup/sim.
- Live investigation identified host saturation source:
  - Docker VM process `com.apple.Virtualization.VirtualMachine` (PID `43521`) was at ~`980%` CPU and ~`18 GB` RSS.
  - Docker VM logs showed repeated `OOM Killer` events for `perl` and container `8342b80c6a1b...` (matching Verilator-perl crash loop symptoms).
  - The runaway container was killed; `docker ps` now shows no running containers.
- End-to-end flow verification is **not complete yet**.

## Local Resource Constraint (Important)
- This work is being debugged on a laptop with limited RAM available to Docker.
- Treat `Error 137` as likely OOM/resource pressure first, not only tool misconfiguration.
- For local repro/debug runs, use moderate parallelism first (likely acceptable on this laptop):
  - `FLOW_JOBS=4` (global cap; can try up to `6` if stable)
  - `VERILATOR_JOBS=4` (can try up to `6` if stable)
  - `SYSTEMC_BUILD_JOBS=4` / `CMAKE_BUILD_PARALLEL_LEVEL=4` (can try up to `6` if stable)
- If `Killed`/`Error 137` returns, step down concurrency to `-j2` then `-j1` as fallback.
- Avoid running multiple heavy flow stages in parallel locally; `make flow` is now serialized by default.
- Keep CI as the final source of truth for full end-to-end confirmation once local sim is stable.

## Changes Already Made

### Simulation Migration
- Deleted old SV testbench: `tb/tb_set_assoc_cache.sv`.
- Added new SystemC testbench: `tb/tb_set_assoc_cache.cpp`.
- Updated simulation runner to Verilator SystemC flow: `scripts/run_sim.sh`.
  - Uses `verilator --sc --timing --build ... --exe tb/tb_set_assoc_cache.cpp`.
  - Exports `SYSTEMC_INCLUDE`, `SYSTEMC_LIBDIR`, and `LD_LIBRARY_PATH`.

### Tooling / Environment
- Extended environment variables for SystemC/Verilator in `scripts/env.sh`:
  - `SYSTEMC_ROOT`, `SYSTEMC_TAG`, `SYSTEMC_BUILD`, `SYSTEMC_INSTALL`, `SYSTEMC_INCLUDE`, `SYSTEMC_LIBDIR`, `VERILATOR_BIN`.
  - Added concurrency controls: `FLOW_JOBS`, `SYSTEMC_BUILD_JOBS`, `VERILATOR_JOBS`, `CMAKE_BUILD_PARALLEL_LEVEL`.
- Extended setup in `scripts/setup_tools.sh`:
  - Clones SystemC `3.0.2` into `.tools/systemc`.
  - Builds and installs SystemC if library is missing.
  - Validates SystemC headers/libs and required tools (`verilator`, `cmake`, `g++`, etc.).
  - Uses bounded `SYSTEMC_BUILD_JOBS` for `cmake --build`.
  - Removed Icarus requirement from setup checks.

### Flow Orchestration
- Updated `Makefile`:
  - `make flow` now calls `scripts/run_all.sh` directly to guarantee stage serialization.
- Updated `scripts/run_sim.sh`:
  - Uses bounded `VERILATOR_JOBS` and prints selected parallelism for easier repro logs.

### Docs (In Progress)
- Updated docs to reflect SystemC/Verilator direction:
  - `AGENTS.md`
  - `README.md`

### Devcontainer
- Updated `.devcontainer/Dockerfile`:
  - Added `cmake`, `g++`.
  - Removed `iverilog` installation.

## What Was Verified
- SystemC `3.0.2` can be cloned/built/installed under `.tools/systemc/install`.
- `libsystemc.so` exists in `.tools/systemc/install/lib`.
- `verilator --get-supported DEV_ASAN` works in the base container in isolation.

## Current Blocker
- Need to re-run container validation after the concurrency mitigation patch:
  - verify `make setup` does not saturate host and OOM during SystemC build,
  - verify `make sim` no longer hits `Killed`/`Error 137` with capped job defaults.
- Docker Desktop VM may retain elevated memory footprint after OOM storms; may require Docker Desktop restart before clean re-test.
- A later manual experiment produced repeated `%Error: ... --get-supported DEV_ASAN` lines, but that run had an invalid `LD_LIBRARY_PATH` setup in the ad-hoc command and is not definitive for the scripted flow.

## Files Currently Modified (Uncommitted)
- `.devcontainer/Dockerfile`
- `AGENTS.md`
- `Makefile`
- `README.md`
- `scripts/env.sh`
- `scripts/run_sim.sh`
- `scripts/setup_tools.sh`
- `tb/tb_set_assoc_cache.cpp` (new)
- `tb/tb_set_assoc_cache.sv` (deleted)

## Remaining Work (Tomorrow)
1. Get `make sim` stable in container:
   - Re-run `make setup` and `make sim` with new default caps (`FLOW_JOBS=4` baseline).
   - Run `bash -x scripts/run_sim.sh` with clean env capture.
   - Split Verilator into generation + make phases to isolate kill point.
   - Confirm memory/oom behavior and adjust options if needed.
   - Use `FLOW_JOBS=4` baseline (optionally `6`), and only step down if OOM recurs.
   - If still unstable, profile container memory limit and reduce peak usage before further tool changes.
2. Once sim passes, run full in-container flow:
   - `make setup`
   - `make sim`
   - `make spike`
   - `make openram`
   - `make synth`
   - `make sta`
   - Keep stages serialized; do not overlap heavy tasks on laptop.
3. Update GitHub CI workflow if any SystemC-specific env/path hooks are still needed after sim stabilizes.
4. Final cleanup and docs consistency pass, then commit.

## Quick Repro Command (Current Failure)
```bash
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" -w /work \
  hpretl/iic-osic-tools:latest --skip bash -lc "make sim"
```
