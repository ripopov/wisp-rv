TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/ram_model.sv
COCOTB_TOPLEVEL := ram_model
COCOTB_TEST_MODULES := test_ram_model
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM
COMPILE_ARGS += -GA_LATENCY=2 -GB_LATENCY=3

include $(shell cocotb-config --makefiles)/Makefile.sim
