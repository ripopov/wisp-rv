# Implementation Plan: Pipelined RV64 Processor

Current implementation stage: **Stage 01 - ISA and decode foundation**.

Assumption: all lower-numbered stages are fully implemented, all tests pass, and changes are merged before work begins on the current stage.

## Target architecture

- 5-stage, single-issue, in-order RV64 pipeline: IF, ID, EX, MEM, WB.
- Primary ISA target: RV64I first, then Zicsr and M extension.
- Verification strategy: cocotb unit tests per module plus end-to-end integration tests that execute real RV64 programs.
- Default simulator: Verilator.

## Bare-metal compiler usage for integration stages

- Required toolchain prefix: `riscv64-unknown-elf-*`.
- ISA flags must match stage capability:
  - Pre-CSR stages: `-march=rv64i -mabi=lp64`
  - CSR-enabled stages: `-march=rv64i_zicsr -mabi=lp64`
  - M-extension stages: `-march=rv64im_zicsr -mabi=lp64`
- Integration tests must compile test programs from source with `riscv64-unknown-elf-gcc`.
- Prebuilt ELF/BIN images are not the source of truth for integration coverage.
- Integration test entrypoints should fail fast when the compiler toolchain is missing.
- Build flow for each integration program:
  1. Compile source to ELF.
  2. Optionally convert ELF to `.bin` if the memory model needs a flat image.
  3. Generate disassembly for debug and retirement-trace checks.

Example commands:

```bash
riscv64-unknown-elf-gcc <isa-flags> -ffreestanding -nostdlib -nostartfiles \
  -T <linker-script.ld> -Wl,-Map,<program>.map -o <program>.elf <program>.S
riscv64-unknown-elf-objcopy -O binary <program>.elf <program>.bin
riscv64-unknown-elf-objdump -d -M no-aliases <program>.elf
```

## Per-stage implementation flow (mandatory)

Apply this workflow to every stage, in order:

1. Write module(s) under `units/<unit-name>/rtl/`.
2. Add a detailed module doc comment to each new RTL module.
3. Write tests under `units/<unit-name>/tb/` and integration tests under `tests/integration/` when stage-level behavior crosses unit boundaries.
4. For integration tests, compile test programs from source using `riscv64-unknown-elf-gcc` with stage-appropriate ISA flags.
5. Run stage-local tests and verify all pass.
6. Run full test suite and verify no regression.
7. Update `ImplementationPlan.md`:
   - advance `Current implementation stage`
   - mark completed stage(s)
   - record any scope changes or deferred work

## Module doc comment standard (mandatory)

Each newly added RTL module must start with a doc comment that includes:

- Module name and purpose.
- Inputs/outputs and key parameters.
- Cycle-level behavior (what happens each cycle).
- Reset behavior.
- Stall/flush/backpressure behavior (if pipelined/handshaked).
- Corner cases and architectural constraints.

Suggested header template:

```systemverilog
/*
 * Module: <module_name>
 * Purpose: <why this module exists>
 * Interface: <key I/O and parameters>
 * Behavior: <cycle-level behavior>
 * Reset: <reset values and semantics>
 * Pipeline control: <stall/flush/forwarding interactions>
 * Corner cases: <special cases and assumptions>
 */
```

## Stage tracker

- [x] Stage 00 - ALU baseline
- [ ] Stage 01 - ISA and decode foundation  <-- current
- [ ] Stage 02 - Register file and pipeline register set
- [ ] Stage 03 - Instruction fetch stage
- [ ] Stage 04 - Execute stage and branch/jump control
- [ ] Stage 05 - Memory stage and load/store unit
- [ ] Stage 06 - Core top-level integration (pipeline v1)
- [ ] Stage 07 - Forwarding and hazard control completion
- [ ] Stage 08 - CSR, exceptions, and interrupts
- [ ] Stage 09 - M extension (multiply/divide)
- [ ] Stage 10 - Memory subsystem integration
- [ ] Stage 11 - Integration program build pipeline (real compiler)
- [ ] Stage 12 - Full-system functional validation
- [ ] Stage 13 - Performance closure and regression gates

---

## Stage 00 - ALU baseline

### Modules we are adding

- `units/alu/rtl/alu.sv` (already implemented).

### Test plan

Functional tests:

1. Directed checks for arithmetic, logical, compare, and shift operations.
2. Randomized vectors for all ALU ops with Python reference model checks.
3. Zero-flag behavior checks.

Performance tests:

1. Confirm ALU remains single-cycle combinational in pipeline integration (no inserted latency).

---

## Stage 01 - ISA and decode foundation

### Modules we are adding

- `units/rv64_pkg/rtl/rv64_pkg.sv` (ISA constants, enums, shared types).
- `units/instr_decoder/rtl/instr_decoder.sv` (instruction field extraction and class decode).
- `units/imm_gen/rtl/imm_gen.sv` (I/S/B/U/J immediate generation for RV64).
- `units/id_control/rtl/id_control.sv` (decode outputs to pipeline control signals).

### Test plan

Functional tests:

1. Decode every RV64I instruction class (R/I/S/B/U/J/system basic).
2. Verify immediate sign-extension and bit placement for all formats.
3. Cross-check randomized instruction words against a Python decode model.

Performance tests:

1. Ensure decode path is purely combinational and produces outputs in one cycle in simulation.
2. Run a high-volume randomized decode test (for example 100k instructions) to catch pathological logic growth and simulation slowdowns.

---

## Stage 02 - Register file and pipeline register set

### Modules we are adding

- `units/regfile/rtl/regfile.sv` (32 x 64-bit register file, 2 read ports, 1 write port, x0 hardwired to zero).
- `units/pipeline_regs/rtl/if_id_reg.sv`
- `units/pipeline_regs/rtl/id_ex_reg.sv`
- `units/pipeline_regs/rtl/ex_mem_reg.sv`
- `units/pipeline_regs/rtl/mem_wb_reg.sv`

### Test plan

Functional tests:

1. Regfile read/write correctness, including same-cycle write/read expectations.
2. x0 immutability checks under random write attempts.
3. Pipeline register hold (stall), clear (flush), and normal advance behavior.

Performance tests:

1. Verify no unintended bubbles are introduced by pipeline register control under steady-state traffic.
2. Stress test long random stall/flush sequences and confirm throughput recovers to one instruction per cycle when stalls are removed.

---

## Stage 03 - Instruction fetch stage

### Modules we are adding

- `units/if_stage/rtl/if_stage.sv` (PC update, fetch request, instruction capture).
- `units/pc_select/rtl/pc_select.sv` (next-PC mux for sequential, branch, jump, trap redirects).
- `units/imem_if/rtl/imem_if.sv` (instruction memory handshake adapter).

### Test plan

Functional tests:

1. Reset vector behavior and sequential PC increment.
2. Correct fetch stall behavior when instruction memory is not ready.
3. Correct redirect behavior for branch/jump/trap PC updates.

Performance tests:

1. Measure fetch throughput on always-ready memory: target one fetch accepted per cycle.
2. Measure redirect penalty in cycles and record baseline for later optimization.

---

## Stage 04 - Execute stage and branch/jump control

### Modules we are adding

- `units/ex_stage/rtl/ex_stage.sv` (operand select, ALU invoke, branch target calculation).
- `units/branch_unit/rtl/branch_unit.sv` (branch condition evaluation).
- `units/jump_unit/rtl/jump_unit.sv` (JAL/JALR target + link behavior).

### Test plan

Functional tests:

1. Branch condition correctness for signed and unsigned comparisons.
2. JAL/JALR target and link register correctness.
3. ALU operand mux correctness for register/immediate/PC-relative operations.

Performance tests:

1. Verify one-cycle execute latency for RV64I integer ops.
2. Measure branch-heavy microbenchmark CPI to establish branch-control baseline.

---

## Stage 05 - Memory stage and load/store unit

### Modules we are adding

- `units/lsu/rtl/lsu.sv` (load/store request generation and response handling).
- `units/load_align/rtl/load_align.sv` (byte/half/word/dword extraction + sign/zero extension).
- `units/store_align/rtl/store_align.sv` (store data/byte-enable generation).
- `units/dmem_if/rtl/dmem_if.sv` (data memory handshake adapter).

### Test plan

Functional tests:

1. Verify all load/store widths and signed/unsigned load semantics.
2. Verify byte-enable generation for subword stores.
3. Verify stall behavior under memory backpressure and correct response matching.
4. Verify exception signaling policy for misaligned accesses (if enabled in this stage).

Performance tests:

1. Measure sustained LSU throughput with always-ready memory (target one accepted memory op per cycle where pipeline dependencies allow).
2. Measure added stall cycles under randomized wait-state injection.

---

## Stage 06 - Core top-level integration (pipeline v1)

### Modules we are adding

- `units/core_top/rtl/core_top.sv` (wires IF/ID/EX/MEM/WB pipeline together).
- `units/wb_mux/rtl/wb_mux.sv` (writeback source select).
- `units/pipeline_ctrl/rtl/pipeline_ctrl.sv` (global valid/stall/flush control, initial version).

### Test plan

Functional tests:

1. Directed short assembly programs: arithmetic chains, branches, simple load/store loops.
2. End-to-end register and memory state checks after program completion.
3. Instruction retirement trace checks against a simple software reference model.

Performance tests:

1. Capture CPI for no-dependency ALU loops (baseline near 1.0, excluding fill/drain effects).
2. Capture CPI for mixed ALU/memory loops to establish baseline before forwarding optimizations.

---

## Stage 07 - Forwarding and hazard control completion

### Modules we are adding

- `units/forwarding_unit/rtl/forwarding_unit.sv` (EX/MEM and MEM/WB bypass selection).
- `units/hazard_unit/rtl/hazard_unit.sv` (load-use hazards, control hazard flush ordering).
- Updates in `units/pipeline_ctrl/rtl/pipeline_ctrl.sv` to enforce deterministic priority between stall and flush.

### Test plan

Functional tests:

1. Back-to-back RAW dependency tests across ALU, load, and branch-producing instructions.
2. Combined hazard scenarios (forwarding + load-use + branch redirect) with expected cycle-by-cycle checks.
3. Randomized dependency-rich instruction streams with scoreboard validation.

Performance tests:

1. Compare CPI against Stage 06 on dependency-heavy microbenchmarks; require measurable improvement.
2. Confirm zero extra bubbles for back-to-back ALU dependencies that are forwardable.

---

## Stage 08 - CSR, exceptions, and interrupts

### Modules we are adding

- `units/csr_file/rtl/csr_file.sv` (machine-level CSRs required for bring-up).
- `units/trap_ctrl/rtl/trap_ctrl.sv` (exception/interrupt entry, cause capture, return path).
- `units/commit_ctrl/rtl/commit_ctrl.sv` (precise exception and commit gating support).

### Test plan

Functional tests:

1. CSR read/write instruction behavior and privilege checks for implemented subset.
2. Illegal instruction, ecall, misaligned access, and breakpoint exception flow.
3. Trap vector entry and `mret` return correctness with pipeline flush verification.

Performance tests:

1. Measure trap entry and return latency in cycles.
2. Confirm no measurable steady-state CPI regression on programs that do not touch CSR/trap paths.

---

## Stage 09 - M extension (multiply/divide)

### Modules we are adding

- `units/mul_unit/rtl/mul_unit.sv` (MUL/MULH/MULHSU/MULHU).
- `units/div_unit/rtl/div_unit.sv` (DIV/DIVU/REM/REMU, including divide-by-zero behavior).
- `units/m_ext_ctrl/rtl/m_ext_ctrl.sv` (multi-cycle op control and pipeline interaction).

### Test plan

Functional tests:

1. Directed edge cases: divide by zero, signed overflow, sign combinations, max/min operands.
2. Randomized operand tests against Python reference model for all M-extension ops.
3. Pipeline control checks for multi-cycle op stalls and correct result writeback timing.

Performance tests:

1. Measure per-op latency and throughput for multiply and divide instructions.
2. Verify non-M instruction streams are not regressed in CPI.

---

## Stage 10 - Memory subsystem integration

### Modules we are adding

- `units/memory_subsystem/rtl/memory_subsystem.sv` (top-level memory fabric for core integration tests).
- `units/ram_model/rtl/ram_model.sv` (deterministic simulation memory model).
- Optional (if enabled in this stage):
  - `units/icache/rtl/icache.sv`
  - `units/dcache/rtl/dcache.sv`

### Test plan

Functional tests:

1. Program loading and deterministic execution against integrated CPU + memory subsystem.
2. Correct instruction and data memory interactions under randomized wait states.
3. If caches are enabled: hit/miss/refill correctness and memory consistency checks.

Performance tests:

1. Measure memory-bound benchmark CPI and memory stall cycle share.
2. If caches are enabled: track hit rate and CPI improvement versus uncached baseline.

---

## Stage 11 - Integration program build pipeline (real compiler)

### Modules we are adding

- `tests/integration/programs/` (bare-metal RV64 assembly/C programs and linker scripts used by tests).
- `tests/integration/linker/` (linker scripts shared by integration test programs).
- `tests/integration/utils/build_rv64_program.py` (wrapper over `riscv64-unknown-elf-*` tools).
- `tests/integration/utils/toolchain.py` (compiler discovery, version checks, and fail-fast diagnostics).
- `tests/integration/test_program_build.py` (compiler pipeline smoke and artifact checks).

### Test plan

Functional tests:

1. Compile representative `.S` and `.c` programs with `riscv64-unknown-elf-gcc` using stage-appropriate ISA flags.
2. Verify required build artifacts are generated (`.elf`, `.map`, disassembly, and optional `.bin`).
3. Verify integration tests consume compiler-generated artifacts, not prebuilt checked-in binaries.
4. Verify toolchain-missing path fails quickly with a clear error message.

Performance tests:

1. Track compile time for the integration program set and establish a CI budget.
2. Evaluate parallel build options to reduce test preparation latency.

---

## Stage 12 - Full-system functional validation

### Modules we are adding

- `tests/integration/test_rv64_programs.py` (curated end-to-end RV64 program suite).
- `tests/integration/test_randomized_streams.py` (randomized long-run integration tests).
- `tests/integration/utils/elf_loader.py` (ELF loading support for simulation harness).
- `tests/integration/utils/reference_model.py` (architectural state checker support).

### Test plan

Functional tests:

1. Build and run a curated RV64 program suite (arithmetic, branch, memory, traps, and M-extension where enabled).
2. Run long randomized instruction streams and compare architectural state against a software reference model.
3. Verify deterministic seed replay and preserve failure artifacts for debug.
4. Verify instruction retirement traces align with compiled program disassembly.

Performance tests:

1. Track total runtime of the full functional integration suite and set an upper bound budget.
2. Track cycles-to-completion for canonical smoke programs to detect major control-path regressions.

---

## Stage 13 - Performance closure and regression gates

### Modules we are adding

- `tests/integration/test_perf_smoke.py` (performance guardrails with threshold checks).
- `tests/integration/benchmarks/` (benchmark program sources compiled with the real toolchain).
- `tests/integration/utils/perf_metrics.py` (CPI/latency collection and trend reporting).

### Test plan

Functional tests:

1. Verify benchmark harness correctness (program start/end detection, cycle counting, metric extraction).
2. Verify each benchmark binary is built from source with `riscv64-unknown-elf-gcc` before simulation.
3. Verify threshold-check logic reports actionable failure output.

Performance tests:

1. Define benchmark set and lock CPI/latency baselines.
2. Add threshold-based regression checks (for example, fail if CPI regresses beyond agreed margin).
3. Track compile-time and simulation-time trends for the benchmark suite.
4. Report stage-over-stage performance trends for branch-heavy and memory-heavy workloads.

---

## Definition of done for each stage

A stage is complete only when all are true:

- All planned modules for the stage are implemented with required doc comments.
- All stage-local functional tests pass.
- Stage-local performance tests pass or documented thresholds are met.
- Full regression passes with no failures.
- `ImplementationPlan.md` is updated (current stage advanced and status tracked).
