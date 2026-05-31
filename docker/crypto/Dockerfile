FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    coreutils \
    gawk \
    grep \
    openssl \
    procps \
    python3 \
    sed \
    tar \
    wget \
    xxd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["bash"]
