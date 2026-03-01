FROM hpretl/iic-osic-tools:latest

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/foss/tools/bin:/foss/tools/sak:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV TOOLCACHE_ROOT=/opt/wisp-tools

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    cmake \
    curl \
    g++ \
    git \
    iverilog \
    make \
    python3 \
    python3-pip \
    verilator \
    && rm -rf /var/lib/apt/lists/*

ARG BAZELISK_VERSION=v1.20.0

RUN arch="$(uname -m)" && \
    case "${arch}" in \
        x86_64) bazelisk_arch="amd64" ;; \
        aarch64|arm64) bazelisk_arch="arm64" ;; \
        *) echo "Unsupported architecture: ${arch}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL -o /usr/local/bin/bazel "https://github.com/bazelbuild/bazelisk/releases/download/${BAZELISK_VERSION}/bazelisk-linux-${bazelisk_arch}" && \
    chmod +x /usr/local/bin/bazel

RUN ln -sf /foss/tools/bin/sta /usr/local/bin/opensta

RUN pip3 install --no-cache-dir coverage

RUN mkdir -p "${TOOLCACHE_ROOT}" && \
    git clone --branch v1.2.48 --depth 1 https://github.com/VLSIDA/OpenRAM.git "${TOOLCACHE_ROOT}/OpenRAM" && \
    git clone --depth 1 --filter=blob:none --sparse https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts.git "${TOOLCACHE_ROOT}/OpenROAD-flow-scripts" && \
    git -C "${TOOLCACHE_ROOT}/OpenROAD-flow-scripts" sparse-checkout set flow/platforms/nangate45 && \
    git clone --branch 3.0.2 --depth 1 https://github.com/accellera-official/systemc.git "${TOOLCACHE_ROOT}/systemc" && \
    cmake -S "${TOOLCACHE_ROOT}/systemc" \
        -B "${TOOLCACHE_ROOT}/systemc/build" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="${TOOLCACHE_ROOT}/systemc/install" && \
    cmake --build "${TOOLCACHE_ROOT}/systemc/build" -j4 && \
    cmake --install "${TOOLCACHE_ROOT}/systemc/build"

RUN command -v bazel >/dev/null && \
    command -v spike >/dev/null && \
    command -v riscv64-unknown-elf-gcc >/dev/null

ENTRYPOINT []
CMD ["sleep", "infinity"]
