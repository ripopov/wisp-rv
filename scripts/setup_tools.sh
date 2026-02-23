#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

mkdir -p "${TOOLS_DIR}"

if [ ! -d "${OPENRAM_ROOT}/.git" ]; then
    git clone --branch v1.2.48 --depth 1 https://github.com/VLSIDA/OpenRAM.git "${OPENRAM_ROOT}"
fi

if [ ! -d "${ORFS_ROOT}/.git" ]; then
    git clone --depth 1 --filter=blob:none --sparse https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git "${ORFS_ROOT}"
    git -C "${ORFS_ROOT}" sparse-checkout set flow/platforms/nangate45
fi

if [ ! -f "${NANGATE45_LIB}" ]; then
    printf "Missing Nangate45 liberty: %s\n" "${NANGATE45_LIB}" >&2
    exit 1
fi

if [ ! -f "${OPENRAM_COMPILER}" ]; then
    printf "Missing OpenRAM compiler: %s\n" "${OPENRAM_COMPILER}" >&2
    exit 1
fi

command -v "${YOSYS_BIN}" >/dev/null
command -v "${OPENSTA_BIN}" >/dev/null
command -v iverilog >/dev/null
command -v python3 >/dev/null
command -v "${SPIKE_BIN}" >/dev/null
command -v "${RISCV_CC_BIN}" >/dev/null

printf "Tool setup complete.\n"
