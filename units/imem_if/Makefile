TOPLEVEL_LANG ?= verilog
SIM ?= verilator

PWD := $(shell pwd)

VERILOG_SOURCES := $(PWD)/rtl/imem_if.sv
VERILOG_SOURCES += $(PWD)/rtl/imem_if_tb_wrap.sv
COCOTB_TOPLEVEL := imem_if_tb_wrap
COCOTB_TEST_MODULES := test_imem_if
export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNSIGNED -Wno-UNUSEDPARAM

include $(shell cocotb-config --makefiles)/Makefile.sim
