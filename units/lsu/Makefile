TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/../rv64_pkg/rtl/rv64_pkg.sv
VERILOG_SOURCES += $(PWD)/../load_align/rtl/load_align.sv
VERILOG_SOURCES += $(PWD)/../store_align/rtl/store_align.sv
VERILOG_SOURCES += $(PWD)/../dmem_if/rtl/dmem_if.sv
VERILOG_SOURCES += $(PWD)/rtl/lsu.sv
COCOTB_TOPLEVEL := lsu
COCOTB_TEST_MODULES := test_lsu
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
