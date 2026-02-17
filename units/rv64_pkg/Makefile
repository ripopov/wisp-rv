TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/rv64_pkg.sv
VERILOG_SOURCES += $(PWD)/rtl/rv64_pkg_sanity.sv
COCOTB_TOPLEVEL := rv64_pkg_sanity
COCOTB_TEST_MODULES := test_rv64_pkg
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
