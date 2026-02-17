TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/../rv64_pkg/rtl/rv64_pkg.sv
VERILOG_SOURCES += $(PWD)/../alu/rtl/alu.sv
VERILOG_SOURCES += $(PWD)/../branch_unit/rtl/branch_unit.sv
VERILOG_SOURCES += $(PWD)/../jump_unit/rtl/jump_unit.sv
VERILOG_SOURCES += $(PWD)/rtl/ex_stage.sv
COCOTB_TOPLEVEL := ex_stage
COCOTB_TEST_MODULES := test_ex_stage
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
