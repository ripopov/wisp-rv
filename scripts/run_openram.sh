#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

if [ ! -d "${OPENRAM_ROOT}/.git" ] || [ ! -f "${NANGATE45_LIB}" ]; then
    "${PROJECT_ROOT}/scripts/setup_tools.sh"
fi

mkdir -p "${OPENRAM_OUT}"

python3 "${OPENRAM_COMPILER}" "${PROJECT_ROOT}/openram/cfg_data_32x64_1rw.py" -p "${OPENRAM_OUT}" -o sram_data_32x64_1rw
python3 "${OPENRAM_COMPILER}" "${PROJECT_ROOT}/openram/cfg_tag_24x64_1rw.py" -p "${OPENRAM_OUT}" -o sram_tag_24x64_1rw

data_lib_candidates=("${OPENRAM_OUT}"/sram_data_32x64_1rw_*.lib)
tag_lib_candidates=("${OPENRAM_OUT}"/sram_tag_24x64_1rw_*.lib)

cp "${data_lib_candidates[0]}" "${OPENRAM_OUT}/sram_data_32x64_1rw.lib"
cp "${tag_lib_candidates[0]}" "${OPENRAM_OUT}/sram_tag_24x64_1rw.lib"

for artifact in \
    "${OPENRAM_OUT}/sram_data_32x64_1rw.v" \
    "${OPENRAM_OUT}/sram_data_32x64_1rw.lib" \
    "${OPENRAM_OUT}/sram_tag_24x64_1rw.v" \
    "${OPENRAM_OUT}/sram_tag_24x64_1rw.lib"; do
    if [ ! -f "${artifact}" ]; then
        printf "Missing expected OpenRAM artifact: %s\n" "${artifact}" >&2
        exit 1
    fi
done

printf "OpenRAM macros generated in %s\n" "${OPENRAM_OUT}"
