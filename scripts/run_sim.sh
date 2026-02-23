#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

mkdir -p "${BUILD_DIR}/sim"

iverilog -g2012 \
    -o "${BUILD_DIR}/sim/tb_set_assoc_cache.vvp" \
    "${PROJECT_ROOT}/rtl/cache_sram_1rw.sv" \
    "${PROJECT_ROOT}/rtl/set_assoc_cache_2way.sv" \
    "${PROJECT_ROOT}/tb/tb_set_assoc_cache.sv"

vvp "${BUILD_DIR}/sim/tb_set_assoc_cache.vvp"
