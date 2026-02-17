# wisp-rv64

RV64 RISC-V core project in SystemVerilog with unit tests in Python (cocotb) and simulation using Verilator.

## Project goals

- Implement an RV64 RISC-V CPU core in SystemVerilog.
- Build reliable verification using Python + cocotb.
- Use Verilator as the default simulator for all verification runs.
- Progress from unit-level tests to full-system end-to-end RV64 program execution.

## Project requirements

- Each hardware unit lives in `units/<unit-name>/`.
- Each unit directory includes:
  - `rtl/` for SystemVerilog RTL
  - `tb/` for cocotb tests
  - `Makefile` for Verilator simulation entrypoint
- Every new unit must include at least one passing cocotb test.
- Unit tests should include both directed edge cases and randomized checks.
- Integration tests for CPU + memory subsystem live in `tests/integration/` and run complete RV64 programs end-to-end.

## Repository layout

- `units/<unit-name>/rtl`: RTL implementation for a unit
- `units/<unit-name>/tb`: cocotb testbench for a unit
- `units/<unit-name>/Makefile`: simulation entrypoint for that unit
- `tests/integration`: top-level CPU + memory subsystem end-to-end tests
- `tests/integration/programs`: bare-metal RV64 program sources used by integration tests
- `tests/integration/linker`: shared linker scripts for integration program builds
- `tests/integration/utils`: toolchain discovery and RV64 build helpers

## Implemented units

- ALU
  - RTL: `units/alu/rtl/alu.sv`
  - Testbench: `units/alu/tb/test_alu.py`
- RV64 ISA package (shared constants/types)
  - RTL: `units/rv64_pkg/rtl/rv64_pkg.sv`
  - Sanity testbench: `units/rv64_pkg/tb/test_rv64_pkg.py`
- Instruction decoder
  - RTL: `units/instr_decoder/rtl/instr_decoder.sv`
  - Testbench: `units/instr_decoder/tb/test_instr_decoder.py`
- Immediate generator
  - RTL: `units/imm_gen/rtl/imm_gen.sv`
  - Testbench: `units/imm_gen/tb/test_imm_gen.py`
- ID control decoder
  - RTL: `units/id_control/rtl/id_control.sv`
  - Testbench: `units/id_control/tb/test_id_control.py`
- Register file
  - RTL: `units/regfile/rtl/regfile.sv`
  - Testbench: `units/regfile/tb/test_regfile.py`
- Pipeline registers
  - RTL: `units/pipeline_regs/rtl/if_id_reg.sv`, `units/pipeline_regs/rtl/id_ex_reg.sv`, `units/pipeline_regs/rtl/ex_mem_reg.sv`, `units/pipeline_regs/rtl/mem_wb_reg.sv`
  - Testbench: `units/pipeline_regs/tb/test_pipeline_regs.py`
- PC select
  - RTL: `units/pc_select/rtl/pc_select.sv`
  - Testbench: `units/pc_select/tb/test_pc_select.py`
- Instruction-memory interface adapter
  - RTL: `units/imem_if/rtl/imem_if.sv`
  - Testbench: `units/imem_if/tb/test_imem_if.py`
- IF stage
  - RTL: `units/if_stage/rtl/if_stage.sv`
  - Testbench: `units/if_stage/tb/test_if_stage.py`
- Branch unit
  - RTL: `units/branch_unit/rtl/branch_unit.sv`
  - Testbench: `units/branch_unit/tb/test_branch_unit.py`
- Jump unit
  - RTL: `units/jump_unit/rtl/jump_unit.sv`
  - Testbench: `units/jump_unit/tb/test_jump_unit.py`
- EX stage
  - RTL: `units/ex_stage/rtl/ex_stage.sv`
  - Testbench: `units/ex_stage/tb/test_ex_stage.py`
- Load align
  - RTL: `units/load_align/rtl/load_align.sv`
  - Testbench: `units/load_align/tb/test_load_align.py`
- Store align
  - RTL: `units/store_align/rtl/store_align.sv`
  - Testbench: `units/store_align/tb/test_store_align.py`
- Data-memory interface adapter
  - RTL: `units/dmem_if/rtl/dmem_if.sv`
  - Testbench: `units/dmem_if/tb/test_dmem_if.py`
- Load/store unit
  - RTL: `units/lsu/rtl/lsu.sv`
  - Testbench: `units/lsu/tb/test_lsu.py`
- WB mux
  - RTL: `units/wb_mux/rtl/wb_mux.sv`
  - Testbench: `units/wb_mux/tb/test_wb_mux.py`
- Forwarding unit
  - RTL: `units/forwarding_unit/rtl/forwarding_unit.sv`
  - Testbench: `units/forwarding_unit/tb/test_forwarding_unit.py`
- Hazard unit
  - RTL: `units/hazard_unit/rtl/hazard_unit.sv`
  - Testbench: `units/hazard_unit/tb/test_hazard_unit.py`
- Multiply unit
  - RTL: `units/mul_unit/rtl/mul_unit.sv`
  - Testbench: `units/mul_unit/tb/test_mul_unit.py`
- Divide/remainder unit
  - RTL: `units/div_unit/rtl/div_unit.sv`
  - Testbench: `units/div_unit/tb/test_div_unit.py`
- M-extension control
  - RTL: `units/m_ext_ctrl/rtl/m_ext_ctrl.sv`
  - Testbench: `units/m_ext_ctrl/tb/test_m_ext_ctrl.py`
- Pipeline control (v2)
  - RTL: `units/pipeline_ctrl/rtl/pipeline_ctrl.sv`
  - Testbench: `units/pipeline_ctrl/tb/test_pipeline_ctrl.py`
- CSR file
  - RTL: `units/csr_file/rtl/csr_file.sv`
  - Testbench: `units/csr_file/tb/test_csr_file.py`
- Trap control
  - RTL: `units/trap_ctrl/rtl/trap_ctrl.sv`
  - Testbench: `units/trap_ctrl/tb/test_trap_ctrl.py`
- Commit control
  - RTL: `units/commit_ctrl/rtl/commit_ctrl.sv`
  - Testbench: `units/commit_ctrl/tb/test_commit_ctrl.py`
- Core top-level integration (v2)
  - RTL: `units/core_top/rtl/core_top.sv`
  - Testbench: `units/core_top/tb/test_core_top.py`
- RAM model
  - RTL: `units/ram_model/rtl/ram_model.sv`
  - Testbench: `units/ram_model/tb/test_ram_model.py`
- Memory subsystem integration top
  - RTL: `units/memory_subsystem/rtl/memory_subsystem.sv`
  - Testbench: `units/memory_subsystem/tb/test_memory_subsystem.py`

Setup Python dependencies (Python 3.13+):

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Run a single unit test:

```bash
PATH="$(pwd)/.venv/bin:$PATH" make -C units/alu SIM=verilator
```

Run all unit tests:

```bash
for dir in units/*/; do
  [ -f "$dir/Makefile" ] && PATH="$(pwd)/.venv/bin:$PATH" make -C "$dir" SIM=verilator
done
```

Run integration tests:

```bash
PATH="$(pwd)/.venv/bin:$PATH" make -C tests/integration SIM=verilator
```

The integration Makefile runs:

- `test_core_top_integration.py`
- `test_rv64_programs.py`
- `test_randomized_streams.py`

Run integration build-pipeline tests:

```bash
PATH="$(pwd)/.venv/bin:$PATH" pytest tests/integration/test_program_build.py
```
