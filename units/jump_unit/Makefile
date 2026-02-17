TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/jump_unit.sv
COCOTB_TOPLEVEL := jump_unit
COCOTB_TEST_MODULES := test_jump_unit
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED

include $(shell cocotb-config --makefiles)/Makefile.sim
