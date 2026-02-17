TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/../../units/rv64_pkg/rtl/rv64_pkg.sv
VERILOG_SOURCES += $(PWD)/../../units/pc_select/rtl/pc_select.sv
VERILOG_SOURCES += $(PWD)/../../units/imem_if/rtl/imem_if.sv
VERILOG_SOURCES += $(PWD)/../../units/if_stage/rtl/if_stage.sv
VERILOG_SOURCES += $(PWD)/../../units/pipeline_regs/rtl/if_id_reg.sv
VERILOG_SOURCES += $(PWD)/../../units/pipeline_regs/rtl/id_ex_reg.sv
VERILOG_SOURCES += $(PWD)/../../units/pipeline_regs/rtl/ex_mem_reg.sv
VERILOG_SOURCES += $(PWD)/../../units/pipeline_regs/rtl/mem_wb_reg.sv
VERILOG_SOURCES += $(PWD)/../../units/instr_decoder/rtl/instr_decoder.sv
VERILOG_SOURCES += $(PWD)/../../units/imm_gen/rtl/imm_gen.sv
VERILOG_SOURCES += $(PWD)/../../units/id_control/rtl/id_control.sv
VERILOG_SOURCES += $(PWD)/../../units/regfile/rtl/regfile.sv
VERILOG_SOURCES += $(PWD)/../../units/alu/rtl/alu.sv
VERILOG_SOURCES += $(PWD)/../../units/branch_unit/rtl/branch_unit.sv
VERILOG_SOURCES += $(PWD)/../../units/jump_unit/rtl/jump_unit.sv
VERILOG_SOURCES += $(PWD)/../../units/ex_stage/rtl/ex_stage.sv
VERILOG_SOURCES += $(PWD)/../../units/load_align/rtl/load_align.sv
VERILOG_SOURCES += $(PWD)/../../units/store_align/rtl/store_align.sv
VERILOG_SOURCES += $(PWD)/../../units/dmem_if/rtl/dmem_if.sv
VERILOG_SOURCES += $(PWD)/../../units/lsu/rtl/lsu.sv
VERILOG_SOURCES += $(PWD)/../../units/wb_mux/rtl/wb_mux.sv
VERILOG_SOURCES += $(PWD)/../../units/forwarding_unit/rtl/forwarding_unit.sv
VERILOG_SOURCES += $(PWD)/../../units/hazard_unit/rtl/hazard_unit.sv
VERILOG_SOURCES += $(PWD)/../../units/mul_unit/rtl/mul_unit.sv
VERILOG_SOURCES += $(PWD)/../../units/div_unit/rtl/div_unit.sv
VERILOG_SOURCES += $(PWD)/../../units/m_ext_ctrl/rtl/m_ext_ctrl.sv
VERILOG_SOURCES += $(PWD)/../../units/csr_file/rtl/csr_file.sv
VERILOG_SOURCES += $(PWD)/../../units/trap_ctrl/rtl/trap_ctrl.sv
VERILOG_SOURCES += $(PWD)/../../units/commit_ctrl/rtl/commit_ctrl.sv
VERILOG_SOURCES += $(PWD)/../../units/pipeline_ctrl/rtl/pipeline_ctrl.sv
VERILOG_SOURCES += $(PWD)/../../units/core_top/rtl/core_top.sv
VERILOG_SOURCES += $(PWD)/../../units/ram_model/rtl/ram_model.sv
VERILOG_SOURCES += $(PWD)/../../units/memory_subsystem/rtl/memory_subsystem.sv
COCOTB_TOPLEVEL := memory_subsystem
COCOTB_TEST_MODULES := test_core_top_integration
export PYTHONPATH := $(PWD):$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
