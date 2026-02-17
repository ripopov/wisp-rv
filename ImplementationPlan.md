# Implementation Plan: Pipelined RV64 Processor

Current implementation stage: **Stage 03 - Instruction fetch stage**.

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

## Cocotb and Verilator testing conventions

These conventions apply to every unit testbench and integration test.

### Makefile template for new units

```makefile
TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/<module>.sv
# When a module depends on the ISA package, list it first:
# VERILOG_SOURCES += <path-to>/units/rv64_pkg/rtl/rv64_pkg.sv
COCOTB_TOPLEVEL := <module>
COCOTB_TEST_MODULES := test_<module>
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED

include $(shell cocotb-config --makefiles)/Makefile.sim
```

### Clock and reset helpers

For sequential modules, use a shared clock and reset pattern:

```python
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

async def reset_dut(dut, cycles=5):
    """Assert active-high synchronous reset for the given number of cycles."""
    dut.rst.value = 1
    await ClockCycles(dut.clk, cycles)
    dut.rst.value = 0
    await RisingEdge(dut.clk)
```

### 64-bit value handling in cocotb + Verilator

Verilator returns signal values as Python integers. Always mask to 64 bits when comparing:

```python
MASK64 = (1 << 64) - 1

def get_u64(signal) -> int:
    """Read a 64-bit signal as unsigned."""
    return int(signal.value) & MASK64
```

Cocotb with Verilator does not support 4-state values (X/Z). All uninitialized signals read as 0. Keep this in mind when checking reset behavior.

### Running all unit tests

```bash
# Run a single unit:
PATH="$(pwd)/.venv/bin:$PATH" make -C units/<unit-name> SIM=verilator

# Run all units (from project root):
for dir in units/*/; do
  [ -f "$dir/Makefile" ] && PATH="$(pwd)/.venv/bin:$PATH" make -C "$dir" SIM=verilator
done
```

## RV64I instruction reference (decode target list)

The decoder must handle every instruction listed below. This is the single source of truth for what Stage 01 must decode. W-suffix instructions (ADDIW, ADDW, etc.) are **RV64I-only** and must not be omitted.

### R-type (opcode 0110011, OP)

| funct7  | funct3 | Mnemonic |
|---------|--------|----------|
| 0000000 | 000    | ADD      |
| 0100000 | 000    | SUB      |
| 0000000 | 001    | SLL      |
| 0000000 | 010    | SLT      |
| 0000000 | 011    | SLTU     |
| 0000000 | 100    | XOR      |
| 0000000 | 101    | SRL      |
| 0100000 | 101    | SRA      |
| 0000000 | 110    | OR       |
| 0000000 | 111    | AND      |

### R-type (opcode 0111011, OP-32) -- RV64I only

| funct7  | funct3 | Mnemonic |
|---------|--------|----------|
| 0000000 | 000    | ADDW     |
| 0100000 | 000    | SUBW     |
| 0000000 | 001    | SLLW     |
| 0000000 | 101    | SRLW     |
| 0100000 | 101    | SRAW     |

### I-type (opcode 0010011, OP-IMM)

| funct3 | Mnemonic | Notes                                      |
|--------|----------|--------------------------------------------|
| 000    | ADDI     |                                            |
| 010    | SLTI     |                                            |
| 011    | SLTIU    |                                            |
| 100    | XORI     |                                            |
| 110    | ORI      |                                            |
| 111    | ANDI     |                                            |
| 001    | SLLI     | shamt = imm[5:0], imm[11:6] must be 000000 |
| 101    | SRLI     | shamt = imm[5:0], imm[11:6] must be 000000 |
| 101    | SRAI     | shamt = imm[5:0], imm[11:6] must be 010000 |

### I-type (opcode 0011011, OP-IMM-32) -- RV64I only

| funct3 | Mnemonic | Notes                                      |
|--------|----------|--------------------------------------------|
| 000    | ADDIW    |                                            |
| 001    | SLLIW    | shamt = imm[4:0], imm[11:5] must be 0000000|
| 101    | SRLIW    | shamt = imm[4:0], imm[11:5] must be 0000000|
| 101    | SRAIW    | shamt = imm[4:0], imm[11:5] must be 0100000|

### Load (opcode 0000011, LOAD)

| funct3 | Mnemonic |
|--------|----------|
| 000    | LB       |
| 001    | LH       |
| 010    | LW       |
| 011    | LD       |
| 100    | LBU      |
| 101    | LHU      |
| 110    | LWU      |

Note: LWU (load word unsigned) is **RV64I-only**. It loads 32 bits and zero-extends to 64 bits. LW sign-extends the 32-bit value to 64 bits.

### Store (opcode 0100011, STORE)

| funct3 | Mnemonic |
|--------|----------|
| 000    | SB       |
| 001    | SH       |
| 010    | SW       |
| 011    | SD       |

### Branch (opcode 1100011, BRANCH)

| funct3 | Mnemonic |
|--------|----------|
| 000    | BEQ      |
| 001    | BNE      |
| 100    | BLT      |
| 101    | BGE      |
| 110    | BLTU     |
| 111    | BGEU     |

### U-type

| opcode  | Mnemonic |
|---------|----------|
| 0110111 | LUI      |
| 0010111 | AUIPC    |

### J-type

| opcode  | Mnemonic |
|---------|----------|
| 1101111 | JAL      |

### I-type jump

| opcode  | funct3 | Mnemonic |
|---------|--------|----------|
| 1100111 | 000    | JALR     |

### System (opcode 1110011)

| funct3 | imm[11:0]    | Mnemonic |
|--------|--------------|----------|
| 000    | 000000000000 | ECALL    |
| 000    | 000000000001 | EBREAK   |

### FENCE (opcode 0001111)

| funct3 | Mnemonic |
|--------|----------|
| 000    | FENCE    |

Note: FENCE is decoded but can be treated as a NOP in this microarchitecture (single-core, in-order, no cache coherence). The decoder must still recognize it as a valid instruction.

## Immediate encoding bit maps (reference)

These bit-level mappings are the ground truth for `imm_gen`. Every bit position must be verified in tests.

```
I-type:  imm[11:0] = instr[31:20]
         sign-extend from bit 11

S-type:  imm[11:5] = instr[31:25], imm[4:0] = instr[11:7]
         sign-extend from bit 11

B-type:  imm[12|10:5] = instr[31:25], imm[4:1|11] = instr[11:7]
         imm[0] is always 0 (halfword-aligned branch targets)
         sign-extend from bit 12

U-type:  imm[31:12] = instr[31:12], imm[11:0] = 0
         sign-extend from bit 31 to 64 bits

J-type:  imm[20|10:1|11|19:12] = instr[31:12]
         imm[0] is always 0
         sign-extend from bit 20
```

Warning: U-type and J-type immediates must be sign-extended to **64 bits** (not 32). This is a common RV64 bug where the upper 32 bits are left as zero instead of sign-extended.

## Pipeline control signal conventions

These conventions govern stall/flush interactions across all pipeline stages. Establish them early (Stage 02) and enforce them consistently.

### Signal naming

- `valid_XX`: instruction in stage XX is architecturally valid (not a bubble).
- `stall_XX`: stage XX must hold its current contents (do not advance).
- `flush_XX`: stage XX contents must be replaced with a bubble.
- `ready_XX`: stage XX can accept new data next cycle.

### Priority rules

1. **Flush takes priority over stall.** If both flush and stall are asserted for the same stage in the same cycle, the stage is flushed (contents are invalidated). Rationale: a redirect (branch, trap) must cancel speculative work even if a downstream stall is active.
2. **Stalls propagate backward.** If stage N is stalled, stages N-1 and earlier must also stall (unless they are being flushed). A stalled stage must not overwrite its contents.
3. **Flush does not propagate backward by default.** A flush clears the target stage's valid bit but does not stall upstream stages. The upstream stage inserts a bubble into the flushed stage on the next cycle.

### Bubble encoding

A bubble (invalid instruction) is represented by deasserting the stage's `valid` bit. The instruction word in a bubble is don't-care, but for debug clarity, NOP encoding (`0x00000013`, ADDI x0, x0, 0) is preferred.

## Stage tracker

- [x] Stage 00 - ALU baseline
- [x] Stage 01 - ISA and decode foundation
- [x] Stage 02 - Register file and pipeline register set
- [ ] Stage 03 - Instruction fetch stage  <-- current
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

### Known pitfalls (resolved)

- Shift amount must use `b[5:0]` (6 bits) for RV64, not `b[4:0]` (5 bits, which is RV32). Already correct in `alu.sv`.
- `$signed()` cast must be applied to both operands in SRA and SLT. Already correct.

---

## Stage 01 - ISA and decode foundation

### Modules we are adding

- `units/rv64_pkg/rtl/rv64_pkg.sv` (ISA constants, enums, shared types).
- `units/instr_decoder/rtl/instr_decoder.sv` (instruction field extraction and class decode).
- `units/imm_gen/rtl/imm_gen.sv` (I/S/B/U/J immediate generation for RV64).
- `units/id_control/rtl/id_control.sv` (decode outputs to pipeline control signals).

### rv64_pkg contents

The package must define at minimum:

- **Opcode constants**: `OP` (0110011), `OP_IMM` (0010011), `OP_32` (0111011), `OP_IMM_32` (0011011), `LOAD` (0000011), `STORE` (0100011), `BRANCH` (1100011), `LUI` (0110111), `AUIPC` (0010111), `JAL` (1101111), `JALR` (1100111), `SYSTEM` (1110011), `FENCE` (0001111).
- **Funct3 constants** for each opcode group (see instruction reference above).
- **ALU operation enum**: matching the `op` encoding used by `alu.sv`.
- **Instruction format enum**: `R_TYPE`, `I_TYPE`, `S_TYPE`, `B_TYPE`, `U_TYPE`, `J_TYPE`.
- **Control signal struct or bundle**: `alu_op`, `alu_src` (reg vs imm), `mem_read`, `mem_write`, `reg_write`, `mem_to_reg`, `branch`, `jump`, `is_word_op` (for W-suffix instructions).

### instr_decoder interface

Inputs:
- `instr[31:0]`: raw 32-bit instruction word.

Outputs:
- `opcode[6:0]`, `rd[4:0]`, `rs1[4:0]`, `rs2[4:0]`, `funct3[2:0]`, `funct7[6:0]`.
- `instr_format`: enum indicating R/I/S/B/U/J.
- `illegal_instr`: asserted when the opcode/funct combination is not recognized.

### imm_gen interface

Inputs:
- `instr[31:0]`: raw instruction word.
- `instr_format`: from decoder.

Outputs:
- `imm[63:0]`: sign-extended 64-bit immediate.

### id_control interface

Inputs:
- `opcode[6:0]`, `funct3[2:0]`, `funct7[6:0]`.

Outputs:
- Control signal struct/bundle (see rv64_pkg).

### Pitfalls and warnings

1. **RV64 shift amount encoding**: For RV64I `SLLI`/`SRLI`/`SRAI`, the shift amount is 6 bits (`imm[5:0]`), and the distinguishing bit for `SRAI` is `imm[11:6] == 010000` (i.e., `instr[30] == 1`). For RV64I W-suffix shifts (`SLLIW`/`SRLIW`/`SRAIW`), the shift amount is 5 bits (`imm[4:0]`), and the distinguishing bit for `SRAIW` is `instr[30] == 1` with `imm[11:5] == 0100000`. This is different from RV32I where all shifts use 5-bit shamt.

2. **OP-32 and OP-IMM-32 opcodes**: These are unique to RV64 and have no RV32 equivalent. They perform 32-bit operations and sign-extend the 32-bit result to 64 bits. The decoder must distinguish `OP` (0110011) from `OP_32` (0111011) and `OP_IMM` (0010011) from `OP_IMM_32` (0011011). A single-bit difference in the opcode.

3. **U-type sign extension to 64 bits**: `LUI` and `AUIPC` produce a 32-bit immediate that must be sign-extended to 64 bits. A common bug is to zero-extend instead, which breaks negative upper immediates.

4. **J-type immediate bit scrambling**: The J-type immediate has a non-obvious bit layout: `instr[31]` = sign, `instr[30:21]` = imm[10:1], `instr[20]` = imm[11], `instr[19:12]` = imm[19:12]. Off-by-one errors in bit selection here are the most common decode bug.

5. **B-type imm[0] is always 0**: The B-type immediate encodes `imm[12:1]` in the instruction. The LSB is implicitly zero. Do not accidentally include `instr[7]` as `imm[0]`; `instr[7]` is `imm[11]`.

6. **Illegal instruction detection**: Must flag any instruction with an unrecognized opcode or an invalid funct3/funct7 combination. This is needed for Stage 08 (exceptions) but should be implemented now so the signal is available. For FENCE, decode it as valid even though the pipeline treats it as NOP.

7. **JALR is I-type, not J-type**: JALR uses I-type immediate encoding (12-bit signed offset from rs1), not the J-type scrambled immediate.

### Test plan

Functional tests:

1. Decode every RV64I instruction listed in the instruction reference above. For each instruction, verify:
   - Correct opcode, rd, rs1, rs2, funct3, funct7 extraction.
   - Correct instruction format classification.
   - Correct immediate value (sign-extended to 64 bits).
   - Correct control signals from id_control.
   - `illegal_instr` is deasserted.
2. Verify immediate sign-extension and bit placement for all formats using directed vectors:
   - I-type: positive and negative immediates, boundary values (-2048, 2047).
   - S-type: composed from split fields, verify reassembly.
   - B-type: verify imm[0] is always 0, verify sign extension from bit 12.
   - U-type: verify upper 20 bits placed correctly, lower 12 bits zero, sign-extended to 64 bits.
   - J-type: verify scrambled bit layout, imm[0] always 0, sign-extended to 64 bits from bit 20.
3. Cross-check randomized instruction words against a Python decode model:
   - Generate valid instruction words for every opcode/format combination.
   - Generate invalid instruction words and verify `illegal_instr` is asserted.
   - Run at least 10k randomized instructions.
4. Specifically test W-suffix instructions (ADDIW, ADDW, SUBW, SLLIW, SRLIW, SRAIW, SLLW, SRLW, SRAW) to verify:
   - Correct opcode discrimination (OP vs OP_32, OP_IMM vs OP_IMM_32).
   - `is_word_op` control signal is asserted.
   - Shift amount widths are correct (5-bit for W, 6-bit for non-W).

Performance tests:

1. Ensure decode path is purely combinational and produces outputs in one cycle in simulation.
2. Run a high-volume randomized decode test (100k instructions) to catch pathological logic growth and simulation slowdowns.

---

## Stage 02 - Register file and pipeline register set

### Modules we are adding

- `units/regfile/rtl/regfile.sv` (32 x 64-bit register file, 2 read ports, 1 write port, x0 hardwired to zero).
- `units/pipeline_regs/rtl/if_id_reg.sv`
- `units/pipeline_regs/rtl/id_ex_reg.sv`
- `units/pipeline_regs/rtl/ex_mem_reg.sv`
- `units/pipeline_regs/rtl/mem_wb_reg.sv`

### regfile interface

```
Inputs:
  clk, rst
  rs1_addr[4:0], rs2_addr[4:0]     -- read port addresses
  wr_en                              -- write enable
  wr_addr[4:0]                       -- write port address
  wr_data[63:0]                      -- write data
Outputs:
  rs1_data[63:0], rs2_data[63:0]     -- read port data
```

### regfile design decisions

- **Write-then-read (bypass) semantics**: If `wr_en` is high and `wr_addr == rs1_addr` (or `rs2_addr`) in the same cycle, the read port must return the new write data, not the stale value. This avoids a structural hazard at the WB/ID boundary. Implement this with an internal bypass mux.
- **x0 hardwiring**: Writes to register 0 are silently ignored. Reads from register 0 always return 0, regardless of write-enable state. Implement by either gating the write or hardcoding the read mux.

### Pipeline register contents

Each pipeline register carries a specific set of fields. Define these as structs in `rv64_pkg`.

**IF/ID register**:
- `pc[63:0]`: PC of the fetched instruction.
- `instr[31:0]`: fetched instruction word.
- `valid`: instruction validity.

**ID/EX register**:
- `pc[63:0]`, `rs1_data[63:0]`, `rs2_data[63:0]`, `imm[63:0]`.
- `rd[4:0]`, `rs1_addr[4:0]`, `rs2_addr[4:0]`.
- `funct3[2:0]`, `funct7[6:0]`.
- Control signals: `alu_op`, `alu_src`, `mem_read`, `mem_write`, `reg_write`, `mem_to_reg`, `branch`, `jump`, `is_word_op`.
- `valid`.

**EX/MEM register**:
- `pc[63:0]`, `alu_result[63:0]`, `rs2_data[63:0]` (store data).
- `rd[4:0]`, `funct3[2:0]`.
- Control signals: `mem_read`, `mem_write`, `reg_write`, `mem_to_reg`, `is_word_op`.
- `branch_taken`: resolved branch decision.
- `branch_target[63:0]`: computed target address.
- `valid`.

**MEM/WB register**:
- `alu_result[63:0]`, `mem_data[63:0]`.
- `rd[4:0]`.
- Control signals: `reg_write`, `mem_to_reg`.
- `valid`.

### Pipeline register control interface

Each pipeline register must support:

```
Inputs:
  clk, rst
  stall   -- hold current contents, do not advance
  flush   -- clear valid bit, insert bubble
  <stage-specific data inputs>
Outputs:
  <stage-specific data outputs>
```

### Pitfalls and warnings

1. **Write-then-read bypass is critical**: Without it, the WB-to-ID path has a one-cycle structural hazard even with forwarding. This bug manifests as incorrect register values when a WB write and ID read target the same register in the same cycle. Test specifically for this case.

2. **x0 bypass interaction**: If the bypass returns write data for `x0`, the hardwiring is broken. The x0 check must take priority over the bypass: `if (addr == 0) return 0; else if (bypass_match) return wr_data; else return reg[addr]`.

3. **Reset clears valid bits, not data**: Pipeline registers should clear their `valid` bit on reset. Clearing all data fields is optional but recommended for simulation cleanliness. Do not rely on data values in invalid pipeline stages.

4. **Stall + flush same cycle**: Follow the priority rule from the pipeline control conventions: flush wins. If both are asserted, the stage is flushed (valid cleared) even though stall is active.

### Test plan

Functional tests:

1. Regfile read/write correctness:
   - Write to every register (x1-x31), read back and verify.
   - Simultaneous write and read to the same register, verify bypass returns new data.
   - Simultaneous write and read to different registers, verify independence.
2. x0 immutability:
   - Write non-zero values to x0 with `wr_en` high, verify reads still return 0.
   - Verify x0 bypass does not leak write data.
3. Pipeline register hold (stall), clear (flush), and normal advance behavior:
   - Drive data in, verify it appears on output after one clock edge.
   - Assert stall, drive new data, verify output holds old data.
   - Assert flush, verify valid deasserted on output.
   - Assert both stall and flush, verify flush takes priority.
4. Pipeline register reset:
   - Verify valid bit is 0 after reset.

Performance tests:

1. Verify no unintended bubbles are introduced by pipeline register control under steady-state traffic.
2. Stress test long random stall/flush sequences and confirm throughput recovers to one instruction per cycle when stalls are removed.

---

## Stage 03 - Instruction fetch stage

### Modules we are adding

- `units/if_stage/rtl/if_stage.sv` (PC update, fetch request, instruction capture).
- `units/pc_select/rtl/pc_select.sv` (next-PC mux for sequential, branch, jump, trap redirects).
- `units/imem_if/rtl/imem_if.sv` (instruction memory handshake adapter).

### if_stage interface

```
Inputs:
  clk, rst
  stall                  -- hold PC, do not advance
  flush                  -- discard current fetch
  redirect_valid         -- a redirect (branch/jump/trap) is requested
  redirect_pc[63:0]      -- target PC for redirect
  imem_rdata[31:0]       -- instruction data from memory
  imem_ready             -- memory can accept a fetch request
Outputs:
  pc[63:0]               -- current PC being fetched
  instr[31:0]            -- fetched instruction
  instr_valid            -- fetch completed and instruction is valid
  imem_addr[63:0]        -- address driven to instruction memory
  imem_req               -- fetch request to memory
```

### pc_select logic

```
if (redirect_valid)
    next_pc = redirect_pc
else if (stall)
    next_pc = current_pc    // hold
else
    next_pc = current_pc + 4
```

### Pitfalls and warnings

1. **Reset PC value**: Define a reset vector (e.g., `0x0000_0000_0000_0000` or `0x0000_0000_8000_0000`). Document it in the module header. All integration tests must place their entry point at this address.

2. **PC increment is +4, not +1**: RV64 uses byte-addressed memory with 32-bit (4-byte) instructions. `PC + 4` is the next sequential instruction, not `PC + 1`.

3. **PC alignment**: The PC must always be 4-byte aligned. Misaligned PC is an exception condition (handled in Stage 08). For now, assert alignment in simulation to catch bugs early.

4. **Redirect timing**: When a branch is resolved in EX (Stage 04), the redirect arrives at IF in the same cycle or the next cycle. The exact timing affects flush depth. Define the convention now: redirect asserted in cycle N means IF captures the new PC in cycle N+1, and the instruction fetched in cycle N (if any) must be flushed.

5. **Stall vs. redirect interaction**: If IF is stalled (e.g., memory not ready) and a redirect arrives, the redirect must take effect. Redirect overrides stall for PC update.

6. **Instruction memory latency**: The imem_if adapter must handle both zero-latency (combinational read, for simple simulation RAMs) and one-cycle latency (registered read) memory models. Start with zero-latency for initial bring-up.

### Test plan

Functional tests:

1. Reset vector behavior: verify PC starts at defined reset address after reset.
2. Sequential PC increment: verify PC advances by 4 each cycle when not stalled/redirected.
3. Redirect: drive `redirect_valid` with a target PC, verify IF captures it on the next cycle.
4. Stall: assert `imem_ready = 0`, verify PC holds and no new fetch is issued.
5. Redirect during stall: assert stall, then assert redirect, verify redirect wins.

Performance tests:

1. Measure fetch throughput on always-ready memory: target one fetch accepted per cycle.
2. Measure redirect penalty in cycles and record baseline for later optimization.

---

## Stage 04 - Execute stage and branch/jump control

### Modules we are adding

- `units/ex_stage/rtl/ex_stage.sv` (operand select, ALU invoke, branch target calculation).
- `units/branch_unit/rtl/branch_unit.sv` (branch condition evaluation).
- `units/jump_unit/rtl/jump_unit.sv` (JAL/JALR target + link behavior).

### ex_stage operand mux

The ALU operand A and B sources depend on instruction type:

| Instruction class | ALU operand A | ALU operand B |
|-------------------|---------------|---------------|
| R-type (OP)       | rs1_data      | rs2_data      |
| I-type (OP-IMM)   | rs1_data      | imm           |
| OP-32 / OP-IMM-32 | rs1_data      | rs2_data / imm| (same as above, but result truncated + sign-extended)|
| Load              | rs1_data      | imm           | (address = rs1 + imm)  |
| Store             | rs1_data      | imm           | (address = rs1 + imm)  |
| Branch            | rs1_data      | rs2_data      | (for comparison); target = PC + imm (separate adder) |
| LUI               | 0             | imm           | (result = imm)         |
| AUIPC             | PC            | imm           | (result = PC + imm)    |
| JAL               | PC            | 4             | (link = PC + 4); target = PC + imm (separate adder) |
| JALR              | PC            | 4             | (link = PC + 4); target = (rs1 + imm) & ~1          |

### branch_unit interface

```
Inputs:
  rs1_data[63:0], rs2_data[63:0]
  funct3[2:0]      -- branch condition selector
  branch           -- instruction is a branch
Outputs:
  branch_taken     -- branch condition is true
```

Branch condition evaluation:

| funct3 | Condition                    |
|--------|------------------------------|
| 000    | BEQ:  rs1 == rs2             |
| 001    | BNE:  rs1 != rs2             |
| 100    | BLT:  signed(rs1) < signed(rs2) |
| 101    | BGE:  signed(rs1) >= signed(rs2) |
| 110    | BLTU: rs1 < rs2 (unsigned)   |
| 111    | BGEU: rs1 >= rs2 (unsigned)  |

### W-suffix instruction result handling

For W-suffix instructions (OP-32, OP-IMM-32), the ALU operates on the full 64-bit values, but the execute stage must:
1. Truncate the ALU result to the lower 32 bits.
2. Sign-extend bit 31 to fill bits [63:32].

This sign-extension is critical: `ADDW x1, x2, x3` where the 32-bit result has bit 31 set must produce a negative 64-bit value in x1.

### Pitfalls and warnings

1. **Branch target = PC + imm, not PC + 4 + imm**: The branch offset is relative to the branch instruction's own PC, not the next instruction. This is a common confusion from architectures with delay slots.

2. **JALR target masking**: JALR target = `(rs1 + imm) & ~1` (clear the LSB). The spec requires this to ensure the target is 2-byte aligned (for C extension compatibility). Forgetting `& ~1` causes misalignment exceptions on some JALR targets.

3. **JALR uses rs1, not PC**: Unlike JAL (which uses PC + imm), JALR computes its target from rs1 + imm. The link address (rd) is PC + 4 for both JAL and JALR.

4. **Signed vs. unsigned branch comparisons**: BLT/BGE use `$signed()` comparison. BLTU/BGEU use unsigned. Using the wrong comparison for any of these is a critical bug that can go undetected by simple tests. Always test with operands near the sign boundary (e.g., `0x7FFFFFFFFFFFFFFF` vs `0x8000000000000000`).

5. **AUIPC destination is rd, not a memory access**: AUIPC writes `PC + imm` to `rd`. It does not access memory. Ensure the control signals route the ALU result to the register write path, not the memory path.

6. **W-suffix sign extension**: The 32-bit result must be sign-extended, not zero-extended. `ADDW` producing `0xFFFFFFFF` must write `0xFFFFFFFF_FFFFFFFF` to rd, not `0x00000000_FFFFFFFF`. This is the most common RV64-specific bug.

### Test plan

Functional tests:

1. Branch condition correctness for all 6 branch types:
   - Equal values, unequal values.
   - Signed comparisons near sign boundary (max positive vs. min negative).
   - Unsigned comparisons near the unsigned boundary (0 vs MAX, MAX vs MAX-1).
2. JAL: verify target = PC + imm, link = PC + 4.
3. JALR: verify target = (rs1 + imm) & ~1, link = PC + 4.
   - Test with odd rs1 + imm sum to verify LSB clearing.
4. AUIPC: verify result = PC + imm, written to rd.
5. LUI: verify result = imm (upper 20 bits placed, lower 12 zero, sign-extended to 64 bits).
6. ALU operand mux correctness for all instruction classes.
7. W-suffix result truncation and sign extension:
   - ADDW with result bit 31 set -> verify negative 64-bit result.
   - ADDW with result bit 31 clear -> verify positive 64-bit result.
   - SUBW, SLLW, SRLW, SRAW with edge cases.

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

### Load alignment and sign extension

The load_align module extracts the correct bytes from a 64-bit memory read based on address offset and funct3:

| funct3 | Width  | Sign extend | Extract bits (addr[2:0]=0) |
|--------|--------|-------------|----------------------------|
| 000 LB | 8-bit  | Yes         | mem[7:0] -> sext to 64     |
| 001 LH | 16-bit | Yes         | mem[15:0] -> sext to 64    |
| 010 LW | 32-bit | Yes         | mem[31:0] -> sext to 64    |
| 011 LD | 64-bit | N/A         | mem[63:0]                  |
| 100 LBU| 8-bit  | No (zero)   | mem[7:0] -> zext to 64     |
| 101 LHU| 16-bit | No (zero)   | mem[15:0] -> zext to 64    |
| 110 LWU| 32-bit | No (zero)   | mem[31:0] -> zext to 64    |

For non-zero address offsets (addr[2:0] != 0), the extract position shifts accordingly. E.g., `LB` at `addr[2:0] = 3` extracts `mem[31:24]`.

### Store alignment and byte enables

The store_align module generates byte-enable signals and positions the store data:

| funct3 | Width  | Byte enables (addr[2:0]=0) |
|--------|--------|----------------------------|
| 000 SB | 8-bit  | 8'b00000001                |
| 001 SH | 16-bit | 8'b00000011                |
| 010 SW | 32-bit | 8'b00001111                |
| 011 SD | 64-bit | 8'b11111111                |

Byte enables shift based on `addr[2:0]`. E.g., `SH` at `addr[2:0] = 2` uses `8'b00001100`.

### Pitfalls and warnings

1. **LW sign-extends, LWU zero-extends**: This is a critical RV64 distinction. `LW` loading `0xFFFFFFFF` from memory must produce `0xFFFFFFFF_FFFFFFFF` (sign-extended). `LWU` loading the same value must produce `0x00000000_FFFFFFFF` (zero-extended). Omitting LWU is a common RV64 bug.

2. **Store data positioning**: For subword stores (SB, SH, SW), the store data must be replicated or shifted to the correct byte lanes. E.g., `SB` stores `rs2[7:0]` to the byte lane selected by `addr[2:0]`. The data on other byte lanes is don't-care (masked by byte enables).

3. **Natural alignment (initial approach)**: For simplicity, require natural alignment in early stages: LH/SH at 2-byte aligned, LW/SW at 4-byte aligned, LD/SD at 8-byte aligned. Misaligned accesses raise an exception (Stage 08). Assert alignment in simulation to catch misalignment early.

4. **Memory interface width**: Use a 64-bit data bus (matching register width) to avoid multi-beat transactions for LD/SD. This simplifies the initial memory stage.

5. **Load data arrives one cycle late**: In a typical pipeline, the load address is computed in EX, the memory is accessed in MEM, and the data is available at the end of MEM. This means load data is not available for forwarding until the WB stage, creating the classic load-use hazard (handled in Stage 07).

### Test plan

Functional tests:

1. Verify all load widths (LB, LH, LW, LD, LBU, LHU, LWU):
   - Load from aligned address, verify correct extraction and sign/zero extension.
   - Load negative values for signed loads, verify sign extension.
   - Load from different byte offsets within a 64-bit word.
2. Verify all store widths (SB, SH, SW, SD):
   - Store to aligned address, verify correct byte enables.
   - Store to different byte offsets, verify byte enable shift.
   - Read back stored data to confirm correctness.
3. Verify stall behavior under memory backpressure (`dmem_ready = 0`).
4. Verify assertion or exception for misaligned accesses.

Performance tests:

1. Measure sustained LSU throughput with always-ready memory (target one accepted memory op per cycle where pipeline dependencies allow).
2. Measure added stall cycles under randomized wait-state injection.

---

## Stage 06 - Core top-level integration (pipeline v1)

### Modules we are adding

- `units/core_top/rtl/core_top.sv` (wires IF/ID/EX/MEM/WB pipeline together).
- `units/wb_mux/rtl/wb_mux.sv` (writeback source select).
- `units/pipeline_ctrl/rtl/pipeline_ctrl.sv` (global valid/stall/flush control, initial version).

### wb_mux writeback sources

| Source    | When selected                              |
|-----------|--------------------------------------------|
| alu_result| Non-memory ALU/branch/LUI/AUIPC operations |
| mem_data  | Load instructions                          |
| pc + 4    | JAL/JALR (link address)                    |

### pipeline_ctrl initial version

Stage 06 uses a simplified pipeline control that handles:
- Sequential instruction flow (no forwarding yet).
- Branch/jump redirects (flush IF and ID stages on taken branch or jump).
- Memory stalls (stall upstream stages when memory is not ready).

Forwarding is **not** implemented in Stage 06. Data hazards are resolved by stalling (or by inserting NOPs in the test programs). This is intentional: Stage 06 validates the basic pipeline structure, and Stage 07 adds forwarding.

### Pitfalls and warnings

1. **Pipeline drain on halt**: Define a program termination convention. Common approach: the test program writes to a special "tohost" address or executes EBREAK. The pipeline must drain (allow all in-flight instructions to complete) before checking final state.

2. **Instruction memory initialization**: The integration test must load the program into instruction memory before simulation starts. Define a standard memory loading mechanism (e.g., a cocotb function that writes instruction words to the memory model).

3. **Branch flush depth**: For a 5-stage pipeline with branches resolved in EX, a taken branch must flush 2 instructions: the one in ID and the one in IF (both were fetched speculatively after the branch). Verify the flush depth is correct.

4. **NOP insertion for hazards (Stage 06 only)**: Without forwarding, test programs must manually insert NOPs between dependent instructions. Document the required NOP count: 2 NOPs between a producing instruction and a consuming instruction (to avoid RAW hazard), 1 NOP after a load before using the loaded value (load-use).

5. **Valid bit propagation**: Each stage must propagate its valid bit to the next. A bubble (valid=0) must not cause a register write, memory access, or branch decision. Verify that invalid instructions in the pipeline are truly inert.

### Test plan

Functional tests:

1. Directed short assembly programs (with manual NOP padding for hazards):
   - Arithmetic chains: `ADDI x1, x0, 5; NOP; NOP; ADDI x2, x1, 10`.
   - Branch: compute value, branch on it, verify correct path taken.
   - Load/store: store a value, load it back, verify register state.
   - LUI + ADDI pattern to construct 32-bit constants.
   - AUIPC + JALR pattern for indirect jumps.
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

### Forwarding paths

```
EX/MEM forwarding (1-cycle bypass):
  if (ex_mem_reg_write && ex_mem_rd != 0 && ex_mem_rd == id_ex_rs1)
      forward rs1 from EX/MEM result

MEM/WB forwarding (2-cycle bypass):
  if (mem_wb_reg_write && mem_wb_rd != 0 && mem_wb_rd == id_ex_rs1
      && NOT (ex_mem_reg_write && ex_mem_rd == id_ex_rs1))  // EX/MEM has priority
      forward rs1 from MEM/WB result
```

Same logic applies independently for rs2.

### Load-use hazard detection

```
if (id_ex_mem_read && id_ex_rd != 0
    && (id_ex_rd == if_id_rs1 || id_ex_rd == if_id_rs2))
    stall IF and ID for one cycle, insert bubble into EX
```

After the one-cycle stall, the load data is available from the MEM/WB forwarding path.

### Pitfalls and warnings

1. **Never forward to x0**: The forwarding conditions must check `rd != 0`. Without this check, an instruction writing to x0 would incorrectly forward a non-zero value to a subsequent instruction reading x0.

2. **EX/MEM forwarding takes priority over MEM/WB**: If both EX/MEM and MEM/WB match the same source register, the EX/MEM value is more recent and must be selected. This handles the case of three back-to-back instructions writing to the same register.

3. **Load-use stall inserts exactly one bubble**: The stall must not be held for more than one cycle. After one stall cycle, the load data is in the MEM/WB register and can be forwarded. If the stall logic accidentally holds for multiple cycles, the pipeline will deadlock.

4. **Forwarding from MEM/WB for load data**: The forwarded value for loads comes from `mem_data` (the memory read output), not `alu_result`. The `mem_to_reg` mux selects the correct value before it reaches the forwarding path. This means the MEM/WB forwarding path must use the final writeback value (post-mux), not just the ALU result.

5. **Branch + forwarding interaction**: A branch instruction in EX may need forwarded operands. The forwarding unit must provide forwarded values to the branch comparator as well as the ALU. If forwarding only feeds the ALU and not the branch unit, branch decisions will use stale register values.

6. **Stall-flush priority with load-use + branch**: If a load-use stall and a branch redirect both fire in the same cycle, the branch redirect should take priority (since the branch result is already resolved). The load-use stall is for a younger instruction that will be flushed anyway.

### Test plan

Functional tests:

1. Back-to-back RAW dependency tests (no NOPs needed):
   - `ADD x1, x0, 5; ADD x2, x1, 10` (EX/MEM forward).
   - `ADD x1, x0, 5; NOP; ADD x2, x1, 10` (MEM/WB forward).
   - `ADD x1, x0, 5; ADD x1, x0, 7; ADD x2, x1, 10` (EX/MEM priority over MEM/WB).
2. Load-use hazard:
   - `LD x1, 0(x2); ADD x3, x1, x4` (one stall cycle, then MEM/WB forward).
   - `LD x1, 0(x2); NOP; ADD x3, x1, x4` (no stall needed, MEM/WB forward).
3. Forwarding with x0:
   - `ADD x0, x0, 5; ADD x1, x0, 10` -> x1 must be 10, not 15.
4. Branch with forwarded operands:
   - `ADD x1, x0, 5; BEQ x1, x2, target` (forwarded x1 to branch comparator).
5. Combined hazard scenarios with expected cycle-by-cycle state checks.
6. Randomized dependency-rich instruction streams with scoreboard validation.

Performance tests:

1. Compare CPI against Stage 06 on dependency-heavy microbenchmarks; require measurable improvement.
2. Confirm zero extra bubbles for back-to-back ALU dependencies that are forwardable.

---

## Stage 08 - CSR, exceptions, and interrupts

### Modules we are adding

- `units/csr_file/rtl/csr_file.sv` (machine-level CSRs required for bring-up).
- `units/trap_ctrl/rtl/trap_ctrl.sv` (exception/interrupt entry, cause capture, return path).
- `units/commit_ctrl/rtl/commit_ctrl.sv` (precise exception and commit gating support).

### Required CSRs (machine-level subset)

| Address | Name      | Description                              |
|---------|-----------|------------------------------------------|
| 0x300   | mstatus   | Machine status (MIE, MPIE, MPP fields)   |
| 0x301   | misa      | ISA description (read-only, hardwired)   |
| 0x304   | mie       | Machine interrupt enable                 |
| 0x305   | mtvec     | Machine trap-handler base address        |
| 0x340   | mscratch  | Scratch register for trap handlers       |
| 0x341   | mepc      | Machine exception PC                     |
| 0x342   | mcause    | Machine trap cause                       |
| 0x343   | mtval     | Machine trap value                       |
| 0x344   | mip       | Machine interrupt pending                |
| 0xF11   | mvendorid | Vendor ID (read-only, 0)                 |
| 0xF12   | marchid   | Architecture ID (read-only, 0)           |
| 0xF13   | mimpid    | Implementation ID (read-only, 0)         |
| 0xF14   | mhartid   | Hart ID (read-only, 0)                   |
| 0xB00   | mcycle    | Cycle counter                            |
| 0xB02   | minstret  | Instructions retired counter             |

### CSR instruction semantics

| Instruction | Operation                                    |
|-------------|----------------------------------------------|
| CSRRW rd, csr, rs1  | t = CSR[csr]; CSR[csr] = rs1; rd = t  |
| CSRRS rd, csr, rs1  | t = CSR[csr]; CSR[csr] = t | rs1; rd = t |
| CSRRC rd, csr, rs1  | t = CSR[csr]; CSR[csr] = t & ~rs1; rd = t |
| CSRRWI rd, csr, zimm | t = CSR[csr]; CSR[csr] = zimm; rd = t |
| CSRRSI rd, csr, zimm | t = CSR[csr]; CSR[csr] = t | zimm; rd = t |
| CSRRCI rd, csr, zimm | t = CSR[csr]; CSR[csr] = t & ~zimm; rd = t |

Note: For CSRRS/CSRRC, if rs1 == x0 (or zimm == 0 for immediate variants), no write occurs (read-only operation). This is how pseudoinstructions like `CSRR rd, csr` (read CSR) and `CSRW csr, rs1` (write CSR) are encoded.

### Trap entry sequence

1. Save current PC to `mepc` (the PC of the trapping instruction, or the next instruction for interrupts).
2. Save cause to `mcause`.
3. Save `mstatus.MIE` to `mstatus.MPIE`, then clear `mstatus.MIE`.
4. Set PC to `mtvec` (BASE field, direct mode: all traps go to BASE).
5. Flush the pipeline.

### MRET sequence

1. Restore `mstatus.MIE` from `mstatus.MPIE`, set `mstatus.MPIE` to 1.
2. Set PC to `mepc`.
3. Flush the pipeline.

### Pitfalls and warnings

1. **CSR read-modify-write atomicity**: CSR instructions read the old value and write the new value in a single atomic operation. The old value is written to rd. If rd == x0 and the operation is CSRRW, the read is skipped (optimization, but functionally optional).

2. **CSRRS/CSRRC with rs1=x0 must not write**: This is a critical spec requirement. `CSRRS x1, mstatus, x0` reads mstatus into x1 but does NOT write mstatus. If the implementation always writes, it will corrupt read-only bits or trigger side effects.

3. **WARL fields**: Many CSR fields are WARL (Write Any values, Read Legal values). The implementation must mask writes to only affect legal bits. E.g., `mstatus` has many reserved fields that must read as 0.

4. **mepc alignment**: `mepc` must be aligned to 4 bytes (IALIGN=32). Writes should mask the lower 2 bits to zero.

5. **Pipeline flush on trap/mret**: Both trap entry and mret must flush all pipeline stages. The flush must happen after the trap/mret instruction commits in WB to ensure precise exceptions.

6. **Exception priority**: When multiple exceptions occur on the same instruction (e.g., illegal instruction + misaligned fetch), the spec defines priorities. For a simple implementation, handle the highest-priority exception and suppress the rest.

7. **mcycle and minstret**: These counters increment every cycle (mcycle) and every committed instruction (minstret). They must be 64 bits wide. If they are CSR-writable, ensure that writes and increments do not race.

### Test plan

Functional tests:

1. CSR read/write for every implemented CSR:
   - CSRRW: write a value, read it back with CSRRS x, csr, x0.
   - CSRRS: set bits, verify only target bits change.
   - CSRRC: clear bits, verify only target bits change.
   - CSRRWI/CSRRSI/CSRRCI with immediate operands.
   - CSRRS with rs1=x0: verify no write occurs.
2. Illegal instruction exception:
   - Execute an undefined opcode, verify trap to mtvec, mepc points to illegal instruction, mcause = 2.
3. ECALL exception:
   - Execute ECALL, verify trap to mtvec, mcause = 11 (M-mode environment call).
4. MRET:
   - Enter trap handler, execute MRET, verify return to mepc, mstatus restored.
5. Nested trap handling (optional): verify mscratch usage pattern.
6. mcycle and minstret: verify they count correctly over a known instruction sequence.

Performance tests:

1. Measure trap entry and return latency in cycles.
2. Confirm no measurable steady-state CPI regression on programs that do not touch CSR/trap paths.

---

## Stage 09 - M extension (multiply/divide)

### Modules we are adding

- `units/mul_unit/rtl/mul_unit.sv` (MUL/MULH/MULHSU/MULHU + MULW).
- `units/div_unit/rtl/div_unit.sv` (DIV/DIVU/REM/REMU + DIVW/DIVUW/REMW/REMUW, including divide-by-zero behavior).
- `units/m_ext_ctrl/rtl/m_ext_ctrl.sv` (multi-cycle op control and pipeline interaction).

### M-extension instructions (RV64)

R-type, opcode OP (0110011), funct7 = 0000001:

| funct3 | Mnemonic | Operation                                  |
|--------|----------|--------------------------------------------|
| 000    | MUL      | rd = (rs1 * rs2)[63:0]                     |
| 001    | MULH     | rd = (signed(rs1) * signed(rs2))[127:64]   |
| 010    | MULHSU   | rd = (signed(rs1) * unsigned(rs2))[127:64] |
| 011    | MULHU    | rd = (unsigned(rs1) * unsigned(rs2))[127:64]|
| 100    | DIV      | rd = signed(rs1) / signed(rs2)             |
| 101    | DIVU     | rd = unsigned(rs1) / unsigned(rs2)         |
| 110    | REM      | rd = signed(rs1) % signed(rs2)             |
| 111    | REMU     | rd = unsigned(rs1) % unsigned(rs2)         |

R-type, opcode OP-32 (0111011), funct7 = 0000001 (RV64 only):

| funct3 | Mnemonic | Operation                                      |
|--------|----------|-------------------------------------------------|
| 000    | MULW     | rd = sext((rs1[31:0] * rs2[31:0])[31:0])       |
| 100    | DIVW     | rd = sext(signed(rs1[31:0]) / signed(rs2[31:0]))|
| 101    | DIVUW    | rd = sext(unsigned(rs1[31:0]) / unsigned(rs2[31:0]))|
| 110    | REMW     | rd = sext(signed(rs1[31:0]) % signed(rs2[31:0]))|
| 111    | REMUW    | rd = sext(unsigned(rs1[31:0]) % unsigned(rs2[31:0]))|

### Division special cases (spec-defined, not exceptions)

| Condition               | DIV result      | REM result |
|--------------------------|-----------------|------------|
| Division by zero         | -1 (all ones)   | Dividend   |
| Signed overflow (-2^63 / -1) | -2^63      | 0          |

These are NOT exceptions in RISC-V. The hardware must produce these specific results.

### Pitfalls and warnings

1. **Division by zero is not an exception**: Unlike x86 and ARM, RISC-V defines the result of division by zero (all-ones for DIV/DIVU, dividend for REM/REMU). The implementation must handle this without trapping.

2. **Signed overflow**: `DIV` of `-2^63 / -1` would overflow the signed range. The spec defines the result as `-2^63` (the dividend). `REM` in this case returns 0.

3. **MULH signed variants**: `MULH` is signed x signed, `MULHU` is unsigned x unsigned, `MULHSU` is signed x unsigned. The sign handling of `MULHSU` is the trickiest: rs1 is treated as signed, rs2 as unsigned. Getting this wrong produces subtle bugs that only manifest with specific sign combinations.

4. **Multi-cycle pipeline stall**: MUL can often be single-cycle (Verilator will synthesize the `*` operator), but DIV is inherently multi-cycle. The `m_ext_ctrl` must stall upstream stages during a divide operation and signal completion. Ensure the stall is released exactly when the result is ready, not one cycle early or late.

5. **W-suffix M-extension**: MULW, DIVW, DIVUW, REMW, REMUW operate on the lower 32 bits of rs1/rs2 and sign-extend the 32-bit result to 64 bits. These must use 32-bit arithmetic, not 64-bit arithmetic truncated to 32 bits (which could give different results for signed operations).

6. **MUL + MULH fusion opportunity**: The spec recommends that `MULH[[S]U] rdh, rs1, rs2; MUL rdl, rs1, rs2` (same rs1, rs2, adjacent instructions) should be fusible. This is an optimization, not required for correctness, but the decoder should be aware of the pattern.

### Test plan

Functional tests:

1. Directed edge cases:
   - Divide by zero for DIV, DIVU, REM, REMU (and W variants): verify spec-defined results.
   - Signed overflow: `-2^63 / -1` for DIV, REM.
   - Sign combinations for MULH, MULHSU, MULHU: positive*positive, positive*negative, negative*positive, negative*negative.
   - Max and min operand values for all operations.
   - W-suffix operations with upper 32 bits non-zero in rs1/rs2 (verify they are ignored).
2. Randomized operand tests against Python reference model for all M-extension ops (including W variants).
3. Pipeline control checks:
   - Verify stall is asserted during multi-cycle divide.
   - Verify no result corruption when a divide is in progress and upstream instructions are stalled.
   - Verify correct result writeback timing (result available exactly when stall is released).

Performance tests:

1. Measure per-op latency for multiply (expect 1 cycle) and divide (record multi-cycle latency).
2. Verify non-M instruction streams are not regressed in CPI.

---

## Stage 10 - Memory subsystem integration

### Modules we are adding

- `units/memory_subsystem/rtl/memory_subsystem.sv` (top-level memory fabric for core integration tests).
- `units/ram_model/rtl/ram_model.sv` (deterministic simulation memory model).
- Optional (if enabled in this stage):
  - `units/icache/rtl/icache.sv`
  - `units/dcache/rtl/dcache.sv`

### Memory subsystem requirements

- Unified or split instruction/data memory interface.
- Support program loading: the testbench must be able to initialize memory contents before simulation starts.
- Deterministic behavior: identical inputs produce identical outputs across simulation runs.
- Configurable latency: support zero-latency (combinational) for fast tests and multi-cycle latency for realistic timing tests.

### ram_model interface

```
Parameters:
  DEPTH           -- number of 64-bit words
  INIT_FILE       -- optional hex file for initialization
Inputs:
  clk
  -- Port A (instruction fetch):
  a_addr[ADDR_W-1:0], a_req
  -- Port B (data load/store):
  b_addr[ADDR_W-1:0], b_req, b_wr, b_wdata[63:0], b_be[7:0]
Outputs:
  a_rdata[31:0], a_ready
  b_rdata[63:0], b_ready
```

### Pitfalls and warnings

1. **Instruction-data memory conflict**: If using unified memory (single-port RAM), simultaneous instruction fetch and data access will conflict. Options: (a) use dual-port RAM, (b) stall instruction fetch during data access, (c) split into separate I-RAM and D-RAM. Dual-port or split is recommended for simplicity.

2. **Memory initialization timing**: In cocotb, memory must be initialized before the first clock edge. Use `$readmemh` in RTL or direct cocotb signal writes before releasing reset.

3. **Byte-addressable vs word-addressable**: The core uses byte addresses (64-bit). The RAM model typically uses word addresses. Ensure the address translation (`byte_addr >> 3` for 64-bit words) is correct and consistent.

4. **Endianness**: RISC-V is little-endian. Byte 0 of a word is at the lowest address. Ensure the memory model, load alignment, and store alignment all agree on byte ordering.

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

### Linker script requirements

The linker script must define:

- `.text` section starting at the reset vector address.
- `.data` section at a known address (accessible by the data memory).
- A `_start` symbol at the entry point.
- Stack pointer initialization (if C programs are used).
- A termination mechanism (e.g., write to a "tohost" address or infinite loop at a known PC).

### Pitfalls and warnings

1. **Toolchain not installed**: The build utility must detect missing toolchain binaries before attempting compilation and produce a clear error message with installation instructions. Use `pytest.skip()` in tests when the toolchain is missing to avoid hard failures in environments without the compiler.

2. **ISA flag mismatch**: Compiling with `-march=rv64im` when the CPU only implements RV64I will produce instructions the pipeline cannot execute. Always use the stage-appropriate ISA flags documented at the top of this file.

3. **Linker script address vs. memory model**: The addresses in the linker script must match the address space of the simulation memory model. A mismatch (e.g., linker puts .text at 0x80000000 but the memory model starts at 0x0) will cause the program to load at the wrong location.

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

### Curated test program categories

1. **Arithmetic**: Integer ALU chains, immediate operations, W-suffix operations.
2. **Branches**: All 6 branch conditions, forward and backward branches, branch-heavy loops.
3. **Jumps**: JAL/JALR call/return patterns, function call conventions.
4. **Memory**: Load/store of all widths, pointer chasing, stack operations.
5. **Hazards**: RAW dependency chains, load-use patterns, branch-after-load.
6. **CSR**: Trap entry/exit, timer reads, interrupt handling.
7. **M-extension**: Multiply/divide operations, edge cases.

### Pitfalls and warnings

1. **ELF loading vs flat binary**: ELF files contain sections at virtual addresses. The loader must respect section addresses, not just dump the file contents at address 0. Use `readelf` or the Python `elftools` library to parse section headers.

2. **Program termination detection**: The testbench must detect when the program finishes. Options: (a) watch for a write to a "tohost" memory-mapped address, (b) detect PC at a known halt address (infinite loop), (c) set a cycle timeout. Implement at least two of these for robustness.

3. **Deterministic simulation**: Seed all random generators with fixed seeds. Record the seed in test output for reproducibility. If a test fails, the seed must be sufficient to reproduce the failure.

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

### Benchmark suite

| Benchmark    | Category    | Key metric           |
|-------------|-------------|----------------------|
| dhrystone   | Integer     | Dhrystones/second    |
| coremark    | Mixed       | CoreMark/MHz         |
| alu_chain   | ALU-bound   | CPI                  |
| branch_maze | Control     | CPI, mispredict rate |
| memcpy      | Memory      | CPI, bandwidth       |

Note: Dhrystone and CoreMark require C compilation with the bare-metal toolchain. Simpler benchmarks (alu_chain, branch_maze, memcpy) can be hand-written assembly.

### CPI targets (initial estimates, to be baselined at Stage 06)

| Workload                | Target CPI |
|-------------------------|------------|
| ALU-only (no hazards)   | 1.0        |
| ALU with dependencies   | 1.0 (with forwarding) |
| Load-use                | 2.0 (one stall cycle) |
| Taken branch            | 3.0 (2-cycle flush penalty) |
| Mixed realistic         | 1.5 - 2.0  |

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
