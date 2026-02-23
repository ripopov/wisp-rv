#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "$0")/env.sh"

EXAMPLE_DIR="${PROJECT_ROOT}/sw/basic"
SPIKE_OUT="${BUILD_DIR}/spike"
ELF_OUT="${SPIKE_OUT}/basic.elf"

for required_file in \
    "${EXAMPLE_DIR}/main.c" \
    "${EXAMPLE_DIR}/start.S" \
    "${EXAMPLE_DIR}/linker.ld"; do
    if [ ! -f "${required_file}" ]; then
        printf "Missing spike example input: %s\n" "${required_file}" >&2
        exit 1
    fi
done

command -v "${SPIKE_BIN}" >/dev/null
command -v "${RISCV_CC_BIN}" >/dev/null

mkdir -p "${SPIKE_OUT}"

"${RISCV_CC_BIN}" \
    -march=rv64imac \
    -mabi=lp64 \
    -mcmodel=medany \
    -msmall-data-limit=0 \
    -nostdlib \
    -nostartfiles \
    -ffreestanding \
    -Wl,-T,"${EXAMPLE_DIR}/linker.ld" \
    -Wl,--no-warn-rwx-segments \
    -Wl,--build-id=none \
    "${EXAMPLE_DIR}/start.S" \
    "${EXAMPLE_DIR}/main.c" \
    -o "${ELF_OUT}"

"${SPIKE_BIN}" --isa=rv64imac "${ELF_OUT}"

printf "Spike bare-metal example passed: %s\n" "${ELF_OUT}"
