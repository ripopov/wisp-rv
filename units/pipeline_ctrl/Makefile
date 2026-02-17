TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/pipeline_ctrl.sv
COCOTB_TOPLEVEL := pipeline_ctrl
COCOTB_TEST_MODULES := test_pipeline_ctrl
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED

include $(shell cocotb-config --makefiles)/Makefile.sim
