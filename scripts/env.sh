#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOOLS_DIR="${TOOLS_DIR:-${PROJECT_ROOT}/.tools}"

export PROJECT_ROOT
export TOOLS_DIR

export OPENRAM_ROOT="${OPENRAM_ROOT:-${TOOLS_DIR}/OpenRAM}"
export ORFS_ROOT="${ORFS_ROOT:-${TOOLS_DIR}/OpenROAD-flow-scripts}"

export OPENRAM_HOME="${OPENRAM_HOME:-${OPENRAM_ROOT}/compiler}"
export OPENRAM_TECH="${OPENRAM_TECH:-${OPENRAM_ROOT}/technology}"

export NANGATE45_ROOT="${NANGATE45_ROOT:-${ORFS_ROOT}/flow/platforms/nangate45}"
export NANGATE45_LIB="${NANGATE45_LIB:-${NANGATE45_ROOT}/lib/NangateOpenCellLibrary_typical.lib}"

export BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
export OPENRAM_OUT="${OPENRAM_OUT:-${BUILD_DIR}/openram}"
export SYNTH_OUT="${SYNTH_OUT:-${BUILD_DIR}/synth}"
export STA_OUT="${STA_OUT:-${PROJECT_ROOT}/reports/sta}"

export YOSYS_BIN="${YOSYS_BIN:-yosys}"
export OPENSTA_BIN="${OPENSTA_BIN:-sta}"
export OPENRAM_COMPILER="${OPENRAM_COMPILER:-${OPENRAM_ROOT}/sram_compiler.py}"
export SPIKE_BIN="${SPIKE_BIN:-spike}"
export RISCV_CC_BIN="${RISCV_CC_BIN:-riscv64-unknown-elf-gcc}"

export PATH="/foss/tools/bin:/foss/tools/sak:${PATH}"
