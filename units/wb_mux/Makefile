TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/wb_mux.sv
COCOTB_TOPLEVEL := wb_mux
COCOTB_TEST_MODULES := test_wb_mux
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED

include $(shell cocotb-config --makefiles)/Makefile.sim
