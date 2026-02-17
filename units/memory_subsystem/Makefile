TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/../rv64_pkg/rtl/rv64_pkg.sv
VERILOG_SOURCES += $(PWD)/../pc_select/rtl/pc_select.sv
VERILOG_SOURCES += $(PWD)/../imem_if/rtl/imem_if.sv
VERILOG_SOURCES += $(PWD)/../if_stage/rtl/if_stage.sv
VERILOG_SOURCES += $(PWD)/../pipeline_regs/rtl/if_id_reg.sv
VERILOG_SOURCES += $(PWD)/../pipeline_regs/rtl/id_ex_reg.sv
VERILOG_SOURCES += $(PWD)/../pipeline_regs/rtl/ex_mem_reg.sv
VERILOG_SOURCES += $(PWD)/../pipeline_regs/rtl/mem_wb_reg.sv
VERILOG_SOURCES += $(PWD)/../instr_decoder/rtl/instr_decoder.sv
VERILOG_SOURCES += $(PWD)/../imm_gen/rtl/imm_gen.sv
VERILOG_SOURCES += $(PWD)/../id_control/rtl/id_control.sv
VERILOG_SOURCES += $(PWD)/../regfile/rtl/regfile.sv
VERILOG_SOURCES += $(PWD)/../alu/rtl/alu.sv
VERILOG_SOURCES += $(PWD)/../branch_unit/rtl/branch_unit.sv
VERILOG_SOURCES += $(PWD)/../jump_unit/rtl/jump_unit.sv
VERILOG_SOURCES += $(PWD)/../ex_stage/rtl/ex_stage.sv
VERILOG_SOURCES += $(PWD)/../load_align/rtl/load_align.sv
VERILOG_SOURCES += $(PWD)/../store_align/rtl/store_align.sv
VERILOG_SOURCES += $(PWD)/../dmem_if/rtl/dmem_if.sv
VERILOG_SOURCES += $(PWD)/../lsu/rtl/lsu.sv
VERILOG_SOURCES += $(PWD)/../wb_mux/rtl/wb_mux.sv
VERILOG_SOURCES += $(PWD)/../forwarding_unit/rtl/forwarding_unit.sv
VERILOG_SOURCES += $(PWD)/../hazard_unit/rtl/hazard_unit.sv
VERILOG_SOURCES += $(PWD)/../mul_unit/rtl/mul_unit.sv
VERILOG_SOURCES += $(PWD)/../div_unit/rtl/div_unit.sv
VERILOG_SOURCES += $(PWD)/../m_ext_ctrl/rtl/m_ext_ctrl.sv
VERILOG_SOURCES += $(PWD)/../csr_file/rtl/csr_file.sv
VERILOG_SOURCES += $(PWD)/../trap_ctrl/rtl/trap_ctrl.sv
VERILOG_SOURCES += $(PWD)/../commit_ctrl/rtl/commit_ctrl.sv
VERILOG_SOURCES += $(PWD)/../pipeline_ctrl/rtl/pipeline_ctrl.sv
VERILOG_SOURCES += $(PWD)/../core_top/rtl/core_top.sv
VERILOG_SOURCES += $(PWD)/../ram_model/rtl/ram_model.sv
VERILOG_SOURCES += $(PWD)/rtl/memory_subsystem.sv
COCOTB_TOPLEVEL := memory_subsystem
COCOTB_TEST_MODULES := test_memory_subsystem
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
