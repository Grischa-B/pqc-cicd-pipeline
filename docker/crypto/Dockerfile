FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ARG OPENSSL_VERSION=3.5.6

ENV OPENSSL_PREFIX=/opt/openssl-3.5
ENV PATH="${OPENSSL_PREFIX}/bin:${PATH}"
ENV LD_LIBRARY_PATH="${OPENSSL_PREFIX}/lib:${LD_LIBRARY_PATH}"

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    build-essential \
    ca-certificates \
    coreutils \
    curl \
    gawk \
    grep \
    make \
    perl \
    procps \
    python3 \
    sed \
    tar \
    wget \
    xxd \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/build

RUN wget -O "openssl-${OPENSSL_VERSION}.tar.gz" "https://www.openssl.org/source/openssl-${OPENSSL_VERSION}.tar.gz" \
    && tar -xzf "openssl-${OPENSSL_VERSION}.tar.gz" \
    && cd "openssl-${OPENSSL_VERSION}" \
    && ./Configure linux-x86_64 \
        --prefix="${OPENSSL_PREFIX}" \
        --openssldir="${OPENSSL_PREFIX}/ssl" \
        --libdir=lib \
        shared \
        zlib \
    && make -j"$(nproc)" \
    && make install_sw install_ssldirs \
    && echo "${OPENSSL_PREFIX}/lib" > /etc/ld.so.conf.d/openssl-3.5.conf \
    && ldconfig \
    && ln -sf "${OPENSSL_PREFIX}/bin/openssl" /usr/local/bin/openssl \
    && cd / \
    && rm -rf /tmp/build

WORKDIR /workspace

RUN openssl version -a \
    && openssl list -providers \
    && openssl list -kem-algorithms | head -50

CMD ["bash"]