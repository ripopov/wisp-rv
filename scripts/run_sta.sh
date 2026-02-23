#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

if [ ! -f "${SYNTH_OUT}/set_assoc_cache_2way_synth.v" ]; then
    "${PROJECT_ROOT}/scripts/run_synth.sh"
fi

mkdir -p "${STA_OUT}"

export SYNTH_NETLIST="${SYNTH_OUT}/set_assoc_cache_2way_synth.v"
export OPENRAM_DATA_LIB="${OPENRAM_OUT}/sram_data_32x64_1rw.lib"
export OPENRAM_TAG_LIB="${OPENRAM_OUT}/sram_tag_24x64_1rw.lib"
export SDC_FILE="${PROJECT_ROOT}/constraints/set_assoc_cache_2way.sdc"

"${OPENSTA_BIN}" "${PROJECT_ROOT}/scripts/opensta_prenpr.tcl"

printf "Pre-PnR STA reports written to %s\n" "${STA_OUT}"
