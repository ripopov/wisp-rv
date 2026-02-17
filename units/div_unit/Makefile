TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/../rv64_pkg/rtl/rv64_pkg.sv
VERILOG_SOURCES += $(PWD)/rtl/div_unit.sv
COCOTB_TOPLEVEL := div_unit
COCOTB_TEST_MODULES := test_div_unit
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
