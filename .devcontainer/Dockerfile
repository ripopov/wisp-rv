FROM hpretl/iic-osic-tools:latest

USER root

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/foss/tools/bin:/foss/tools/sak:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    make \
    python3 \
    python3-pip \
    iverilog \
    verilator \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /foss/tools/bin/sta /usr/local/bin/opensta

ENTRYPOINT []
CMD ["sleep", "infinity"]
