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

if [ ! -d "${SYSTEMC_ROOT}/.git" ]; then
    git clone --branch "${SYSTEMC_TAG}" --depth 1 https://github.com/accellera-official/systemc.git "${SYSTEMC_ROOT}"
fi

if ! compgen -G "${SYSTEMC_LIBDIR}/libsystemc.*" >/dev/null; then
    systemc_build_jobs="${SYSTEMC_BUILD_JOBS}"
    if ! [[ "${systemc_build_jobs}" =~ ^[0-9]+$ ]] || [ "${systemc_build_jobs}" -lt 1 ]; then
        systemc_build_jobs=1
    fi
    export CMAKE_BUILD_PARALLEL_LEVEL="${systemc_build_jobs}"
    printf "Building SystemC with %s job(s)\n" "${systemc_build_jobs}"

    cmake -S "${SYSTEMC_ROOT}" \
        -B "${SYSTEMC_BUILD}" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="${SYSTEMC_INSTALL}"

    cmake --build "${SYSTEMC_BUILD}" -j"${systemc_build_jobs}"
    cmake --install "${SYSTEMC_BUILD}"

    if ! compgen -G "${SYSTEMC_LIBDIR}/libsystemc.*" >/dev/null && [ -d "${SYSTEMC_INSTALL}/lib64" ]; then
        export SYSTEMC_LIBDIR="${SYSTEMC_INSTALL}/lib64"
    fi
fi

if [ ! -f "${NANGATE45_LIB}" ]; then
    printf "Missing Nangate45 liberty: %s\n" "${NANGATE45_LIB}" >&2
    exit 1
fi

if [ ! -f "${OPENRAM_COMPILER}" ]; then
    printf "Missing OpenRAM compiler: %s\n" "${OPENRAM_COMPILER}" >&2
    exit 1
fi

if [ ! -f "${SYSTEMC_INCLUDE}/systemc" ]; then
    printf "Missing SystemC include entrypoint: %s\n" "${SYSTEMC_INCLUDE}/systemc" >&2
    exit 1
fi

if ! compgen -G "${SYSTEMC_LIBDIR}/libsystemc.*" >/dev/null; then
    printf "Missing SystemC library under: %s\n" "${SYSTEMC_LIBDIR}" >&2
    exit 1
fi

command -v "${YOSYS_BIN}" >/dev/null
command -v "${OPENSTA_BIN}" >/dev/null
command -v "${WISP_VERILATOR_CMD}" >/dev/null
command -v python3 >/dev/null
command -v pip3 >/dev/null
command -v cmake >/dev/null
command -v g++ >/dev/null
command -v "${SPIKE_BIN}" >/dev/null
command -v "${RISCV_CC_BIN}" >/dev/null

if ! python3 -c "import coverage" >/dev/null 2>&1; then
    printf "Installing missing Python package: coverage\n"
    pip3 install --user coverage
fi

printf "Tool setup complete.\n"
