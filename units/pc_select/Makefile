TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/pc_select.sv
COCOTB_TOPLEVEL := pc_select
COCOTB_TEST_MODULES := test_pc_select
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED

include $(shell cocotb-config --makefiles)/Makefile.sim
