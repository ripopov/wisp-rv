TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/../pc_select/rtl/pc_select.sv
VERILOG_SOURCES += $(PWD)/../imem_if/rtl/imem_if.sv
VERILOG_SOURCES += $(PWD)/rtl/if_stage.sv
COCOTB_TOPLEVEL := if_stage
COCOTB_TEST_MODULES := test_if_stage
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
