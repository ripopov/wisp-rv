#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

if [ ! -f "${OPENRAM_OUT}/sram_data_32x64_1rw.v" ] || [ ! -f "${OPENRAM_OUT}/sram_tag_24x64_1rw.v" ]; then
    "${PROJECT_ROOT}/scripts/run_openram.sh"
fi

if [ ! -f "${NANGATE45_LIB}" ]; then
    "${PROJECT_ROOT}/scripts/setup_tools.sh"
fi

mkdir -p "${SYNTH_OUT}"

"${YOSYS_BIN}" -p "read_verilog -sv -D USE_OPENRAM_MACROS ${PROJECT_ROOT}/rtl/cache_sram_1rw.sv ${PROJECT_ROOT}/rtl/set_assoc_cache_2way.sv; read_verilog -lib ${OPENRAM_OUT}/sram_data_32x64_1rw.v ${OPENRAM_OUT}/sram_tag_24x64_1rw.v; hierarchy -check -top set_assoc_cache_2way; synth -top set_assoc_cache_2way; dfflibmap -liberty ${NANGATE45_LIB}; abc -liberty ${NANGATE45_LIB}; stat -liberty ${NANGATE45_LIB}; write_verilog -noattr ${SYNTH_OUT}/set_assoc_cache_2way_synth.v"

printf "Synthesis netlist written to %s\n" "${SYNTH_OUT}/set_assoc_cache_2way_synth.v"
