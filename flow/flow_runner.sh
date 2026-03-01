#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${BUILD_WORKSPACE_DIRECTORY:-$(pwd)}"
cd "${PROJECT_ROOT}"

detect_jobs() {
    local detected_jobs

    detected_jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || printf '4')"
    if ! [[ "${detected_jobs}" =~ ^[0-9]+$ ]] || [ "${detected_jobs}" -lt 1 ]; then
        detected_jobs=4
    fi

    if [ "${detected_jobs}" -gt 4 ]; then
        detected_jobs=4
    fi

    printf '%s\n' "${detected_jobs}"
}

clamp_jobs() {
    local value="$1"
    local max_value="$2"

    if ! [[ "${value}" =~ ^[0-9]+$ ]] || [ "${value}" -lt 1 ]; then
        value=1
    fi

    if ! [[ "${max_value}" =~ ^[0-9]+$ ]] || [ "${max_value}" -lt 1 ]; then
        max_value=4
    fi

    if [ "${value}" -gt "${max_value}" ]; then
        value="${max_value}"
    fi

    printf '%s\n' "${value}"
}

require_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" >/dev/null; then
        printf 'Missing required command: %s\n' "${cmd}" >&2
        exit 1
    fi
}

require_file() {
    local file="$1"
    if [ ! -f "${file}" ]; then
        printf 'Missing required file: %s\n' "${file}" >&2
        exit 1
    fi
}

init_env() {
    local max_parallel_jobs
    local flow_jobs
    local verilator_jobs

    max_parallel_jobs="${MAX_PARALLEL_JOBS:-4}"
    if ! [[ "${max_parallel_jobs}" =~ ^[0-9]+$ ]] || [ "${max_parallel_jobs}" -lt 1 ]; then
        max_parallel_jobs=4
    fi

    flow_jobs="${FLOW_JOBS:-$(detect_jobs)}"
    flow_jobs="$(clamp_jobs "${flow_jobs}" "${max_parallel_jobs}")"

    verilator_jobs="${VERILATOR_JOBS:-${flow_jobs}}"
    verilator_jobs="$(clamp_jobs "${verilator_jobs}" "${max_parallel_jobs}")"

    export MAX_PARALLEL_JOBS="${max_parallel_jobs}"
    export FLOW_JOBS="${flow_jobs}"
    export VERILATOR_JOBS="${verilator_jobs}"

    if [ -z "${OPENRAM_ROOT:-}" ]; then
        if [ -d "/opt/wisp-tools/OpenRAM" ]; then
            OPENRAM_ROOT="/opt/wisp-tools/OpenRAM"
        elif [ -d "${PROJECT_ROOT}/.tools/OpenRAM" ]; then
            OPENRAM_ROOT="${PROJECT_ROOT}/.tools/OpenRAM"
        else
            OPENRAM_ROOT="/opt/wisp-tools/OpenRAM"
        fi
    fi

    if [ -z "${ORFS_ROOT:-}" ]; then
        if [ -d "/opt/wisp-tools/OpenROAD-flow-scripts" ]; then
            ORFS_ROOT="/opt/wisp-tools/OpenROAD-flow-scripts"
        elif [ -d "${PROJECT_ROOT}/.tools/OpenROAD-flow-scripts" ]; then
            ORFS_ROOT="${PROJECT_ROOT}/.tools/OpenROAD-flow-scripts"
        else
            ORFS_ROOT="/opt/wisp-tools/OpenROAD-flow-scripts"
        fi
    fi

    if [ -z "${SYSTEMC_ROOT:-}" ]; then
        if [ -d "/opt/wisp-tools/systemc" ]; then
            SYSTEMC_ROOT="/opt/wisp-tools/systemc"
        elif [ -d "${PROJECT_ROOT}/.tools/systemc" ]; then
            SYSTEMC_ROOT="${PROJECT_ROOT}/.tools/systemc"
        else
            SYSTEMC_ROOT="/opt/wisp-tools/systemc"
        fi
    fi

    export OPENRAM_ROOT
    export ORFS_ROOT
    export SYSTEMC_ROOT

    export OPENRAM_HOME="${OPENRAM_HOME:-${OPENRAM_ROOT}/compiler}"
    export OPENRAM_TECH="${OPENRAM_TECH:-${OPENRAM_ROOT}/technology}"
    export OPENRAM_COMPILER="${OPENRAM_COMPILER:-${OPENRAM_ROOT}/sram_compiler.py}"

    export SYSTEMC_INSTALL="${SYSTEMC_INSTALL:-${SYSTEMC_ROOT}/install}"
    export SYSTEMC_INCLUDE="${SYSTEMC_INCLUDE:-${SYSTEMC_INSTALL}/include}"

    if [ -z "${SYSTEMC_LIBDIR:-}" ]; then
        if compgen -G "${SYSTEMC_INSTALL}/lib/libsystemc.*" >/dev/null; then
            SYSTEMC_LIBDIR="${SYSTEMC_INSTALL}/lib"
        elif compgen -G "${SYSTEMC_INSTALL}/lib64/libsystemc.*" >/dev/null; then
            SYSTEMC_LIBDIR="${SYSTEMC_INSTALL}/lib64"
        else
            SYSTEMC_LIBDIR="${SYSTEMC_INSTALL}/lib"
        fi
    fi
    export SYSTEMC_LIBDIR

    export NANGATE45_ROOT="${NANGATE45_ROOT:-${ORFS_ROOT}/flow/platforms/nangate45}"
    export NANGATE45_LIB="${NANGATE45_LIB:-${NANGATE45_ROOT}/lib/NangateOpenCellLibrary_typical.lib}"

    export BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
    export OPENRAM_OUT="${OPENRAM_OUT:-${BUILD_DIR}/openram}"
    export SYNTH_OUT="${SYNTH_OUT:-${BUILD_DIR}/synth}"
    export STA_OUT="${STA_OUT:-${PROJECT_ROOT}/reports/sta}"

    export YOSYS_BIN="${YOSYS_BIN:-yosys}"
    export OPENSTA_BIN="${OPENSTA_BIN:-sta}"
    export WISP_VERILATOR_CMD="${WISP_VERILATOR_CMD:-verilator}"
    export SPIKE_BIN="${SPIKE_BIN:-spike}"
    export RISCV_CC_BIN="${RISCV_CC_BIN:-riscv64-unknown-elf-gcc}"

    export PATH="/foss/tools/bin:/foss/tools/sak:${PATH}"
}

require_systemc() {
    require_file "${SYSTEMC_INCLUDE}/systemc"
    if ! compgen -G "${SYSTEMC_LIBDIR}/libsystemc.*" >/dev/null; then
        printf 'Missing SystemC library under: %s\n' "${SYSTEMC_LIBDIR}" >&2
        exit 1
    fi
}

stage_openram() {
    local -a data_lib_candidates
    local -a tag_lib_candidates

    require_cmd python3
    require_file "${OPENRAM_COMPILER}"

    mkdir -p "${OPENRAM_OUT}"

    python3 "${OPENRAM_COMPILER}" "${PROJECT_ROOT}/openram/cfg_data_32x64_1rw.py" -p "${OPENRAM_OUT}" -o sram_data_32x64_1rw
    python3 "${OPENRAM_COMPILER}" "${PROJECT_ROOT}/openram/cfg_tag_24x64_1rw.py" -p "${OPENRAM_OUT}" -o sram_tag_24x64_1rw

    shopt -s nullglob
    data_lib_candidates=("${OPENRAM_OUT}"/sram_data_32x64_1rw_*.lib)
    tag_lib_candidates=("${OPENRAM_OUT}"/sram_tag_24x64_1rw_*.lib)
    shopt -u nullglob

    if [ "${#data_lib_candidates[@]}" -eq 0 ]; then
        printf 'Missing generated OpenRAM data liberty in %s\n' "${OPENRAM_OUT}" >&2
        exit 1
    fi
    if [ "${#tag_lib_candidates[@]}" -eq 0 ]; then
        printf 'Missing generated OpenRAM tag liberty in %s\n' "${OPENRAM_OUT}" >&2
        exit 1
    fi

    cp "${data_lib_candidates[0]}" "${OPENRAM_OUT}/sram_data_32x64_1rw.lib"
    cp "${tag_lib_candidates[0]}" "${OPENRAM_OUT}/sram_tag_24x64_1rw.lib"

    require_file "${OPENRAM_OUT}/sram_data_32x64_1rw.v"
    require_file "${OPENRAM_OUT}/sram_data_32x64_1rw.lib"
    require_file "${OPENRAM_OUT}/sram_tag_24x64_1rw.v"
    require_file "${OPENRAM_OUT}/sram_tag_24x64_1rw.lib"

    printf 'OpenRAM macros generated in %s\n' "${OPENRAM_OUT}"
}

stage_sim() {
    local sim_jobs
    local sim_obj_dir

    require_systemc
    require_cmd "${WISP_VERILATOR_CMD}"

    mkdir -p "${BUILD_DIR}/sim"

    export LD_LIBRARY_PATH="${SYSTEMC_LIBDIR}:${LD_LIBRARY_PATH:-}"

    sim_jobs="$(clamp_jobs "${VERILATOR_JOBS}" "${MAX_PARALLEL_JOBS}")"
    sim_obj_dir="${BUILD_DIR}/sim/obj_dir"
    rm -rf "${sim_obj_dir}"

    printf 'Running Verilator build with %s job(s)\n' "${sim_jobs}"

    env -u VERILATOR_BIN "${WISP_VERILATOR_CMD}" \
        --sc \
        --timing \
        --build \
        -j "${sim_jobs}" \
        --Mdir "${sim_obj_dir}" \
        --top-module set_assoc_cache_2way \
        -Wno-DECLFILENAME \
        -Wno-UNUSEDSIGNAL \
        -CFLAGS "-std=c++17" \
        -LDFLAGS "-Wl,-rpath,${SYSTEMC_LIBDIR}" \
        --exe "${PROJECT_ROOT}/tb/tb_set_assoc_cache.cpp" \
        -o tb_set_assoc_cache_sim \
        "${PROJECT_ROOT}/rtl/cache_sram_1rw.sv" \
        "${PROJECT_ROOT}/rtl/set_assoc_cache_2way.sv"

    "${sim_obj_dir}/tb_set_assoc_cache_sim"
}

stage_spike() {
    local example_dir
    local spike_out
    local elf_out

    require_cmd "${SPIKE_BIN}"
    require_cmd "${RISCV_CC_BIN}"

    example_dir="${PROJECT_ROOT}/sw/basic"
    spike_out="${BUILD_DIR}/spike"
    elf_out="${spike_out}/basic.elf"

    require_file "${example_dir}/main.c"
    require_file "${example_dir}/start.S"
    require_file "${example_dir}/linker.ld"

    mkdir -p "${spike_out}"

    "${RISCV_CC_BIN}" \
        -march=rv64imac \
        -mabi=lp64 \
        -mcmodel=medany \
        -msmall-data-limit=0 \
        -nostdlib \
        -nostartfiles \
        -ffreestanding \
        -Wl,-T,"${example_dir}/linker.ld" \
        -Wl,--no-warn-rwx-segments \
        -Wl,--build-id=none \
        "${example_dir}/start.S" \
        "${example_dir}/main.c" \
        -o "${elf_out}"

    "${SPIKE_BIN}" --isa=rv64imac "${elf_out}"

    printf 'Spike bare-metal example passed: %s\n' "${elf_out}"
}

stage_synth() {
    require_cmd "${YOSYS_BIN}"
    require_file "${NANGATE45_LIB}"

    if [ ! -f "${OPENRAM_OUT}/sram_data_32x64_1rw.v" ] || [ ! -f "${OPENRAM_OUT}/sram_tag_24x64_1rw.v" ]; then
        stage_openram
    fi

    mkdir -p "${SYNTH_OUT}"

    "${YOSYS_BIN}" -p "read_verilog -sv -D USE_OPENRAM_MACROS ${PROJECT_ROOT}/rtl/cache_sram_1rw.sv ${PROJECT_ROOT}/rtl/set_assoc_cache_2way.sv; read_verilog -lib ${OPENRAM_OUT}/sram_data_32x64_1rw.v ${OPENRAM_OUT}/sram_tag_24x64_1rw.v; hierarchy -check -top set_assoc_cache_2way; synth -top set_assoc_cache_2way; dfflibmap -liberty ${NANGATE45_LIB}; abc -liberty ${NANGATE45_LIB}; stat -liberty ${NANGATE45_LIB}; write_verilog -noattr ${SYNTH_OUT}/set_assoc_cache_2way_synth.v"

    printf 'Synthesis netlist written to %s\n' "${SYNTH_OUT}/set_assoc_cache_2way_synth.v"
}

stage_sta() {
    require_cmd "${OPENSTA_BIN}"
    require_file "${NANGATE45_LIB}"
    require_file "${PROJECT_ROOT}/scripts/opensta_prenpr.tcl"

    if [ ! -f "${SYNTH_OUT}/set_assoc_cache_2way_synth.v" ]; then
        stage_synth
    fi

    mkdir -p "${STA_OUT}"

    export SYNTH_NETLIST="${SYNTH_OUT}/set_assoc_cache_2way_synth.v"
    export OPENRAM_DATA_LIB="${OPENRAM_OUT}/sram_data_32x64_1rw.lib"
    export OPENRAM_TAG_LIB="${OPENRAM_OUT}/sram_tag_24x64_1rw.lib"
    export SDC_FILE="${PROJECT_ROOT}/constraints/set_assoc_cache_2way.sdc"

    require_file "${SYNTH_NETLIST}"
    require_file "${OPENRAM_DATA_LIB}"
    require_file "${OPENRAM_TAG_LIB}"
    require_file "${SDC_FILE}"

    "${OPENSTA_BIN}" "${PROJECT_ROOT}/scripts/opensta_prenpr.tcl"

    printf 'Pre-PnR STA reports written to %s\n' "${STA_OUT}"
}

stage_all() {
    stage_openram
    stage_sim
    stage_spike
    stage_synth
    stage_sta
}

stage_clean() {
    rm -rf "${BUILD_DIR}" "${PROJECT_ROOT}/reports/sta" "${PROJECT_ROOT}/reports/ci"
    printf 'Removed generated outputs under %s and reports/{sta,ci}.\n' "${BUILD_DIR}"
}

main() {
    local stage="${1:-}"

    init_env

    case "${stage}" in
        openram)
            stage_openram
            ;;
        sim)
            stage_sim
            ;;
        spike)
            stage_spike
            ;;
        synth)
            stage_synth
            ;;
        sta)
            stage_sta
            ;;
        all)
            stage_all
            ;;
        clean)
            stage_clean
            ;;
        *)
            printf 'Usage: %s {openram|sim|spike|synth|sta|all|clean}\n' "$0" >&2
            exit 1
            ;;
    esac
}

main "$@"
