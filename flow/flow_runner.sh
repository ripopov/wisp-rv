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

float_ge() {
    local lhs="$1"
    local rhs="$2"
    awk -v a="${lhs}" -v b="${rhs}" 'BEGIN { exit (a >= b) ? 0 : 1 }'
}

parse_wns_max() {
    local report_path="$1"
    awk '/worst[[:space:]]+slack[[:space:]]+max/ { print $4; exit }' "${report_path}"
}

parse_tns_max() {
    local report_path="$1"
    awk '/tns[[:space:]]+max/ { print $3; exit }' "${report_path}"
}

render_period_sdc() {
    local template_path="$1"
    local period_ns="$2"
    local output_path="$3"

    sed "s/__PERIOD_NS__/${period_ns}/g" "${template_path}" > "${output_path}"
}

write_study_result_success() {
    local result_dir="$1"
    local design_name="$2"
    local category="$3"
    local top_module="$4"
    local period_ns="$5"
    local fmax_mhz="$6"
    local wns_ns="$7"
    local tns_ns="$8"

    cat > "${result_dir}/result.json" <<EOF
{
  "design_name": "${design_name}",
  "category": "${category}",
  "top_module": "${top_module}",
  "clock_period_ns_at_wns_zero": ${period_ns},
  "fmax_mhz": ${fmax_mhz},
  "wns_ns": ${wns_ns},
  "tns_ns": ${tns_ns},
  "status": "success",
  "error_message": "",
  "report_dir": "${result_dir}"
}
EOF
}

write_study_result_failure() {
    local result_dir="$1"
    local design_name="$2"
    local category="$3"
    local top_module="$4"
    local error_message="$5"

    cat > "${result_dir}/result.json" <<EOF
{
  "design_name": "${design_name}",
  "category": "${category}",
  "top_module": "${top_module}",
  "clock_period_ns_at_wns_zero": null,
  "fmax_mhz": null,
  "wns_ns": null,
  "tns_ns": null,
  "status": "failure",
  "error_message": "${error_message}",
  "report_dir": "${result_dir}"
}
EOF
}

run_study_sta_once() {
    local top_module="$1"
    local netlist_path="$2"
    local sdc_template="$3"
    local period_ns="$4"
    local run_dir="$5"
    local extra_libs="$6"
    local run_sdc="${run_dir}/run.sdc"

    mkdir -p "${run_dir}"
    render_period_sdc "${sdc_template}" "${period_ns}" "${run_sdc}"

    export STUDY_TOP="${top_module}"
    export STUDY_NETLIST="${netlist_path}"
    export STUDY_SDC="${run_sdc}"
    export STUDY_EXTRA_LIBS="${extra_libs}"
    export STA_OUT="${run_dir}"

    "${OPENSTA_BIN}" "${PROJECT_ROOT}/scripts/opensta_prenpr_study.tcl"
}

search_study_fmax() {
    local design_name="$1"
    local category="$2"
    local top_module="$3"
    local netlist_path="$4"
    local sdc_template="$5"
    local extra_libs="$6"
    local result_dir="$7"

    local low_period_ns
    local high_period_ns
    local best_period_ns
    local best_wns_ns
    local best_tns_ns
    local wns_ns
    local tns_ns
    local mid_period_ns
    local fmax_mhz
    local expand_round

    low_period_ns="0.200000"
    high_period_ns="10.000000"
    best_period_ns=""
    best_wns_ns=""
    best_tns_ns=""
    expand_round=0

    mkdir -p "${result_dir}"

    while true; do
        if ! run_study_sta_once "${top_module}" "${netlist_path}" "${sdc_template}" "${high_period_ns}" "${result_dir}" "${extra_libs}"; then
            write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "opensta_failed"
            return 1
        fi

        wns_ns="$(parse_wns_max "${result_dir}/wns_max.rpt" || true)"
        tns_ns="$(parse_tns_max "${result_dir}/tns.rpt" || true)"
        if [ -z "${wns_ns}" ] || [ -z "${tns_ns}" ]; then
            write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "sta_report_parse_failed"
            return 1
        fi

        if float_ge "${wns_ns}" "0.0"; then
            best_period_ns="${high_period_ns}"
            best_wns_ns="${wns_ns}"
            best_tns_ns="${tns_ns}"
            break
        fi

        if float_ge "${high_period_ns}" "20.0"; then
            write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "timing_not_met_at_20ns"
            return 1
        fi

        high_period_ns="$(awk -v period="${high_period_ns}" 'BEGIN { next_period = period * 2.0; if (next_period > 20.0) next_period = 20.0; printf "%.6f", next_period }')"
        expand_round=$((expand_round + 1))
        if [ "${expand_round}" -gt 8 ] && float_ge "${high_period_ns}" "20.0"; then
            write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "timing_search_failed_to_expand"
            return 1
        fi
    done

    for _ in $(seq 1 18); do
        mid_period_ns="$(awk -v low="${low_period_ns}" -v high="${high_period_ns}" 'BEGIN { printf "%.6f", (low + high) / 2.0 }')"

        if ! run_study_sta_once "${top_module}" "${netlist_path}" "${sdc_template}" "${mid_period_ns}" "${result_dir}" "${extra_libs}"; then
            write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "opensta_failed_during_binary_search"
            return 1
        fi

        wns_ns="$(parse_wns_max "${result_dir}/wns_max.rpt" || true)"
        tns_ns="$(parse_tns_max "${result_dir}/tns.rpt" || true)"
        if [ -z "${wns_ns}" ] || [ -z "${tns_ns}" ]; then
            write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "sta_report_parse_failed_during_binary_search"
            return 1
        fi

        if float_ge "${wns_ns}" "0.0"; then
            high_period_ns="${mid_period_ns}"
            best_period_ns="${mid_period_ns}"
            best_wns_ns="${wns_ns}"
            best_tns_ns="${tns_ns}"
        else
            low_period_ns="${mid_period_ns}"
        fi
    done

    if ! run_study_sta_once "${top_module}" "${netlist_path}" "${sdc_template}" "${best_period_ns}" "${result_dir}" "${extra_libs}"; then
        write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "opensta_failed_at_final_period"
        return 1
    fi

    best_wns_ns="$(parse_wns_max "${result_dir}/wns_max.rpt" || true)"
    best_tns_ns="$(parse_tns_max "${result_dir}/tns.rpt" || true)"
    if [ -z "${best_wns_ns}" ] || [ -z "${best_tns_ns}" ]; then
        write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "sta_report_parse_failed_at_final_period"
        return 1
    fi

    if ! float_ge "${best_wns_ns}" "0.0"; then
        write_study_result_failure "${result_dir}" "${design_name}" "${category}" "${top_module}" "wns_negative_at_final_period"
        return 1
    fi

    fmax_mhz="$(awk -v period="${best_period_ns}" 'BEGIN { printf "%.3f", 1000.0 / period }')"
    write_study_result_success "${result_dir}" "${design_name}" "${category}" "${top_module}" "${best_period_ns}" "${fmax_mhz}" "${best_wns_ns}" "${best_tns_ns}"

    printf 'Explore result %-24s period=%s ns fmax=%s MHz\n' "${design_name}" "${best_period_ns}" "${fmax_mhz}"
    return 0
}

calc_addr_bits() {
    local num_words="$1"
    local bits
    local remaining

    bits=0
    remaining=$((num_words - 1))
    while [ "${remaining}" -gt 0 ]; do
        bits=$((bits + 1))
        remaining=$((remaining >> 1))
    done

    if [ "${bits}" -lt 1 ]; then
        bits=1
    fi

    printf '%s\n' "${bits}"
}

generate_ram_wrapper() {
    local wrapper_path="$1"
    local top_module="$2"
    local macro_name="$3"
    local word_size="$4"
    local addr_bits="$5"
    local word_msb
    local addr_msb

    word_msb=$((word_size - 1))
    addr_msb=$((addr_bits - 1))

    cat > "${wrapper_path}" <<EOF
module ${top_module} (
    input  logic                 clk,
    input  logic                 rst_n,
    input  logic                 in_csb,
    input  logic                 in_web,
    input  logic [${addr_msb}:0]  in_addr,
    input  logic [${word_msb}:0]  in_din,
    output logic [${word_msb}:0]  out_dout
);
    logic                  csb_q;
    logic                  web_q;
    logic [${addr_msb}:0]  addr_q;
    logic [${word_msb}:0]  din_q;
    logic [${word_msb}:0]  ram_dout;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            csb_q <= 1'b1;
            web_q <= 1'b1;
            addr_q <= '0;
            din_q <= '0;
        end else begin
            csb_q <= in_csb;
            web_q <= in_web;
            addr_q <= in_addr;
            din_q <= in_din;
        end
    end

    ${macro_name} u_ram (
        .clk0(clk),
        .csb0(csb_q),
        .web0(web_q),
        .addr0(addr_q),
        .din0(din_q),
        .dout0(ram_dout)
    );

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            out_dout <= '0;
        end else begin
            out_dout <= ram_dout;
        end
    end
endmodule
EOF
}

stage_explore_nangate45() {
    local study_name
    local study_build_root
    local study_report_root
    local cfg_dir
    local openram_dir
    local synth_dir
    local wrappers_dir
    local per_design_dir
    local manifest_path
    local failures
    local design_result_dir
    local design_name
    local top_module
    local rtl_path
    local sdc_template
    local netlist_path
    local macro_name
    local cfg_path
    local word_size
    local num_words
    local macro_v
    local macro_lib
    local wrapper_path
    local addr_bits
    local ram_design_name
    local ram_top_module
    local ram_sdc_template
    local -a ram_matrix
    local -a ram_entries
    local -a lib_candidates
    local -a logic_entries

    require_cmd python3
    require_cmd "${YOSYS_BIN}"
    require_cmd "${OPENSTA_BIN}"

    require_file "${OPENRAM_COMPILER}"
    require_file "${NANGATE45_LIB}"
    require_file "${PROJECT_ROOT}/scripts/gen_openram_cfg_matrix.py"
    require_file "${PROJECT_ROOT}/scripts/generate_explore_report.py"
    require_file "${PROJECT_ROOT}/scripts/opensta_prenpr_study.tcl"
    require_file "${PROJECT_ROOT}/constraints/bench/bench_ram_wrap.sdc"

    study_name="nangate45_openram_freepdk45"
    study_build_root="${BUILD_DIR}/studies/${study_name}"
    study_report_root="${PROJECT_ROOT}/reports/studies/${study_name}"
    cfg_dir="${study_build_root}/openram_cfg"
    openram_dir="${study_build_root}/openram"
    synth_dir="${study_build_root}/synth"
    wrappers_dir="${study_build_root}/wrappers"
    per_design_dir="${study_report_root}/per_design"
    manifest_path="${study_report_root}/matrix.json"
    failures=0

    rm -rf "${study_build_root}" "${study_report_root}"
    mkdir -p "${cfg_dir}" "${openram_dir}" "${synth_dir}" "${wrappers_dir}" "${per_design_dir}"

    mapfile -t ram_matrix < <(
        python3 "${PROJECT_ROOT}/scripts/gen_openram_cfg_matrix.py" \
            --out-dir "${cfg_dir}" \
            --manifest-json "${manifest_path}"
    )
    if [ "${#ram_matrix[@]}" -eq 0 ]; then
        printf 'No OpenRAM matrix entries generated for exploration target.\n' >&2
        exit 1
    fi

    ram_entries=()
    for entry in "${ram_matrix[@]}"; do
        IFS=$'\t' read -r macro_name cfg_path word_size num_words <<< "${entry}"
        if [ -z "${macro_name}" ] || [ -z "${cfg_path}" ] || [ -z "${word_size}" ] || [ -z "${num_words}" ]; then
            printf 'Invalid matrix row: %s\n' "${entry}" >&2
            exit 1
        fi

        python3 "${OPENRAM_COMPILER}" "${cfg_path}" -p "${openram_dir}" -o "${macro_name}"

        shopt -s nullglob
        lib_candidates=("${openram_dir}/${macro_name}"_*.lib)
        shopt -u nullglob
        if [ "${#lib_candidates[@]}" -eq 0 ]; then
            printf 'Missing generated OpenRAM liberty for %s in %s\n' "${macro_name}" "${openram_dir}" >&2
            exit 1
        fi

        cp "${lib_candidates[0]}" "${openram_dir}/${macro_name}.lib"
        require_file "${openram_dir}/${macro_name}.v"
        require_file "${openram_dir}/${macro_name}.lib"

        ram_entries+=("${macro_name}|${word_size}|${num_words}|${openram_dir}/${macro_name}.v|${openram_dir}/${macro_name}.lib")
    done

    logic_entries=(
        "bench_add32_pipe|bench_add32_pipe|${PROJECT_ROOT}/rtl/bench/bench_add32_pipe.sv|${PROJECT_ROOT}/constraints/bench/bench_add32_pipe.sdc"
        "bench_mux8x32_pipe|bench_mux8x32_pipe|${PROJECT_ROOT}/rtl/bench/bench_mux8x32_pipe.sv|${PROJECT_ROOT}/constraints/bench/bench_mux8x32_pipe.sdc"
        "bench_cmp64_pipe|bench_cmp64_pipe|${PROJECT_ROOT}/rtl/bench/bench_cmp64_pipe.sv|${PROJECT_ROOT}/constraints/bench/bench_cmp64_pipe.sdc"
        "bench_fifo_ctrl_small|bench_fifo_ctrl_small|${PROJECT_ROOT}/rtl/bench/bench_fifo_ctrl_small.sv|${PROJECT_ROOT}/constraints/bench/bench_fifo_ctrl_small.sdc"
    )

    for entry in "${logic_entries[@]}"; do
        IFS='|' read -r design_name top_module rtl_path sdc_template <<< "${entry}"
        design_result_dir="${per_design_dir}/${design_name}"
        netlist_path="${synth_dir}/${design_name}/${design_name}_synth.v"
        mkdir -p "${design_result_dir}" "$(dirname "${netlist_path}")"

        if ! "${YOSYS_BIN}" -p "read_verilog -sv ${rtl_path}; hierarchy -check -top ${top_module}; synth -top ${top_module}; dfflibmap -liberty ${NANGATE45_LIB}; abc -liberty ${NANGATE45_LIB}; stat -liberty ${NANGATE45_LIB}; write_verilog -noattr ${netlist_path}"; then
            write_study_result_failure "${design_result_dir}" "${design_name}" "logic" "${top_module}" "yosys_synth_failed"
            failures=$((failures + 1))
            continue
        fi

        if ! search_study_fmax "${design_name}" "logic" "${top_module}" "${netlist_path}" "${sdc_template}" "" "${design_result_dir}"; then
            failures=$((failures + 1))
        fi
    done

    ram_sdc_template="${PROJECT_ROOT}/constraints/bench/bench_ram_wrap.sdc"
    for entry in "${ram_entries[@]}"; do
        IFS='|' read -r macro_name word_size num_words macro_v macro_lib <<< "${entry}"

        ram_design_name="ram_${word_size}x${num_words}"
        ram_top_module="bench_ram_wrap_${word_size}x${num_words}_1rw"
        design_result_dir="${per_design_dir}/${ram_design_name}"
        netlist_path="${synth_dir}/${ram_design_name}/${ram_design_name}_synth.v"
        wrapper_path="${wrappers_dir}/${ram_top_module}.sv"

        mkdir -p "${design_result_dir}" "$(dirname "${netlist_path}")"

        addr_bits="$(calc_addr_bits "${num_words}")"
        generate_ram_wrapper "${wrapper_path}" "${ram_top_module}" "${macro_name}" "${word_size}" "${addr_bits}"

        if ! "${YOSYS_BIN}" -p "read_verilog -sv ${wrapper_path}; read_verilog -lib ${macro_v}; hierarchy -check -top ${ram_top_module}; synth -top ${ram_top_module}; dfflibmap -liberty ${NANGATE45_LIB}; abc -liberty ${NANGATE45_LIB}; stat -liberty ${NANGATE45_LIB}; write_verilog -noattr ${netlist_path}"; then
            write_study_result_failure "${design_result_dir}" "${ram_design_name}" "ram" "${ram_top_module}" "yosys_synth_failed"
            failures=$((failures + 1))
            continue
        fi

        if ! search_study_fmax "${ram_design_name}" "ram" "${ram_top_module}" "${netlist_path}" "${ram_sdc_template}" "${macro_lib}" "${design_result_dir}"; then
            failures=$((failures + 1))
        fi
    done

    python3 "${PROJECT_ROOT}/scripts/generate_explore_report.py" \
        --results-dir "${per_design_dir}" \
        --output-md "${study_report_root}/summary.md" \
        --output-json "${study_report_root}/summary.json"

    if [ "${failures}" -gt 0 ]; then
        printf 'Exploration completed with %s failing design(s). See %s\n' "${failures}" "${study_report_root}/summary.md" >&2
        exit 1
    fi

    printf 'Exploration study reports written to %s\n' "${study_report_root}"
}

stage_all() {
    stage_openram
    stage_sim
    stage_spike
    stage_synth
    stage_sta
}

stage_clean() {
    rm -rf "${BUILD_DIR}" "${PROJECT_ROOT}/reports/sta" "${PROJECT_ROOT}/reports/ci" "${PROJECT_ROOT}/reports/studies"
    printf 'Removed generated outputs under %s and reports/{sta,ci,studies}.\n' "${BUILD_DIR}"
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
        explore_nangate45)
            stage_explore_nangate45
            ;;
        all)
            stage_all
            ;;
        clean)
            stage_clean
            ;;
        *)
            printf 'Usage: %s {openram|sim|spike|synth|sta|explore_nangate45|all|clean}\n' "$0" >&2
            exit 1
            ;;
    esac
}

main "$@"
