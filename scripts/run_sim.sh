#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

mkdir -p "${BUILD_DIR}/sim"

if [ ! -f "${SYSTEMC_INCLUDE}/systemc" ] || ! compgen -G "${SYSTEMC_LIBDIR}/libsystemc.*" >/dev/null; then
    "${PROJECT_ROOT}/scripts/setup_tools.sh"
fi

command -v "${VERILATOR_BIN}" >/dev/null

export SYSTEMC_INCLUDE
export SYSTEMC_LIBDIR
export LD_LIBRARY_PATH="${SYSTEMC_LIBDIR}:${LD_LIBRARY_PATH:-}"

SIM_OBJ_DIR="${BUILD_DIR}/sim/obj_dir"
sim_jobs="${VERILATOR_JOBS}"
if ! [[ "${sim_jobs}" =~ ^[0-9]+$ ]] || [ "${sim_jobs}" -lt 1 ]; then
    sim_jobs=1
fi
printf "Running Verilator build with %s job(s)\n" "${sim_jobs}"

"${VERILATOR_BIN}" \
    --sc \
    --timing \
    --build \
    -j "${sim_jobs}" \
    --Mdir "${SIM_OBJ_DIR}" \
    --top-module set_assoc_cache_2way \
    -Wno-DECLFILENAME \
    -Wno-UNUSEDSIGNAL \
    -CFLAGS "-std=c++17" \
    -LDFLAGS "-Wl,-rpath,${SYSTEMC_LIBDIR}" \
    --exe "${PROJECT_ROOT}/tb/tb_set_assoc_cache.cpp" \
    -o tb_set_assoc_cache_sim \
    "${PROJECT_ROOT}/rtl/cache_sram_1rw.sv" \
    "${PROJECT_ROOT}/rtl/set_assoc_cache_2way.sv"

"${SIM_OBJ_DIR}/tb_set_assoc_cache_sim"
