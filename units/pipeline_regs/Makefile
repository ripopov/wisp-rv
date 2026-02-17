TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/../rv64_pkg/rtl/rv64_pkg.sv
VERILOG_SOURCES += $(PWD)/rtl/if_id_reg.sv
VERILOG_SOURCES += $(PWD)/rtl/id_ex_reg.sv
VERILOG_SOURCES += $(PWD)/rtl/ex_mem_reg.sv
VERILOG_SOURCES += $(PWD)/rtl/mem_wb_reg.sv
VERILOG_SOURCES += $(PWD)/rtl/pipeline_regs_tb_wrap.sv
COCOTB_TOPLEVEL := pipeline_regs_tb_wrap
COCOTB_TEST_MODULES := test_pipeline_regs
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
