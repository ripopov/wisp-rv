#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${TOOLS_DIR:-${PROJECT_ROOT}/.tools}"

export PROJECT_ROOT
export TOOLS_DIR

detected_jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf "4")"
if ! [[ "${detected_jobs}" =~ ^[0-9]+$ ]] || [ "${detected_jobs}" -lt 1 ]; then
    detected_jobs=4
fi
if [ "${detected_jobs}" -gt 4 ]; then
    detected_jobs=4
fi

export FLOW_JOBS="${FLOW_JOBS:-${detected_jobs}}"
export SYSTEMC_BUILD_JOBS="${SYSTEMC_BUILD_JOBS:-${FLOW_JOBS}}"
export VERILATOR_JOBS="${VERILATOR_JOBS:-${FLOW_JOBS}}"
export CMAKE_BUILD_PARALLEL_LEVEL="${CMAKE_BUILD_PARALLEL_LEVEL:-${SYSTEMC_BUILD_JOBS}}"
export MAX_PARALLEL_JOBS="${MAX_PARALLEL_JOBS:-4}"

if ! [[ "${MAX_PARALLEL_JOBS}" =~ ^[0-9]+$ ]] || [ "${MAX_PARALLEL_JOBS}" -lt 1 ]; then
    MAX_PARALLEL_JOBS=4
fi

for job_var in FLOW_JOBS SYSTEMC_BUILD_JOBS VERILATOR_JOBS CMAKE_BUILD_PARALLEL_LEVEL; do
    job_val="${!job_var}"
    if ! [[ "${job_val}" =~ ^[0-9]+$ ]] || [ "${job_val}" -lt 1 ]; then
        printf "Warning: %s=%s is invalid; using 1\n" "${job_var}" "${job_val}" >&2
        export "${job_var}=1"
        continue
    fi

    if [ "${job_val}" -gt "${MAX_PARALLEL_JOBS}" ]; then
        printf "Warning: %s=%s exceeds MAX_PARALLEL_JOBS=%s; clamping to %s\n" \
            "${job_var}" "${job_val}" "${MAX_PARALLEL_JOBS}" "${MAX_PARALLEL_JOBS}" >&2
        export "${job_var}=${MAX_PARALLEL_JOBS}"
    fi
done

export OPENRAM_ROOT="${OPENRAM_ROOT:-${TOOLS_DIR}/OpenRAM}"
export ORFS_ROOT="${ORFS_ROOT:-${TOOLS_DIR}/OpenROAD-flow-scripts}"

export OPENRAM_HOME="${OPENRAM_HOME:-${OPENRAM_ROOT}/compiler}"
export OPENRAM_TECH="${OPENRAM_TECH:-${OPENRAM_ROOT}/technology}"
export SYSTEMC_ROOT="${SYSTEMC_ROOT:-${TOOLS_DIR}/systemc}"
export SYSTEMC_TAG="${SYSTEMC_TAG:-3.0.2}"
export SYSTEMC_BUILD="${SYSTEMC_BUILD:-${SYSTEMC_ROOT}/build}"
export SYSTEMC_INSTALL="${SYSTEMC_INSTALL:-${SYSTEMC_ROOT}/install}"
export SYSTEMC_INCLUDE="${SYSTEMC_INCLUDE:-${SYSTEMC_INSTALL}/include}"
export SYSTEMC_LIBDIR="${SYSTEMC_LIBDIR:-${SYSTEMC_INSTALL}/lib}"

if [ ! -f "${SYSTEMC_LIBDIR}/libsystemc.so" ] && [ ! -f "${SYSTEMC_LIBDIR}/libsystemc.dylib" ] && [ -d "${SYSTEMC_INSTALL}/lib64" ]; then
    export SYSTEMC_LIBDIR="${SYSTEMC_INSTALL}/lib64"
fi

export NANGATE45_ROOT="${NANGATE45_ROOT:-${ORFS_ROOT}/flow/platforms/nangate45}"
export NANGATE45_LIB="${NANGATE45_LIB:-${NANGATE45_ROOT}/lib/NangateOpenCellLibrary_typical.lib}"

export BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
export OPENRAM_OUT="${OPENRAM_OUT:-${BUILD_DIR}/openram}"
export SYNTH_OUT="${SYNTH_OUT:-${BUILD_DIR}/synth}"
export STA_OUT="${STA_OUT:-${PROJECT_ROOT}/reports/sta}"

export YOSYS_BIN="${YOSYS_BIN:-yosys}"
export OPENSTA_BIN="${OPENSTA_BIN:-sta}"
export OPENRAM_COMPILER="${OPENRAM_COMPILER:-${OPENRAM_ROOT}/sram_compiler.py}"
# Use a project-specific variable name to avoid clobbering Verilator's own
# VERILATOR_BIN environment knob (used internally by the wrapper script).
export WISP_VERILATOR_CMD="${WISP_VERILATOR_CMD:-verilator}"
export SPIKE_BIN="${SPIKE_BIN:-spike}"
export RISCV_CC_BIN="${RISCV_CC_BIN:-riscv64-unknown-elf-gcc}"

export PATH="/foss/tools/bin:/foss/tools/sak:${PATH}"
