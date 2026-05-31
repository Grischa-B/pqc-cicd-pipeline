#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${1:-pqc-crypto-base:local}"

echo "[crypto] Inspecting image: ${IMAGE_NAME}"
echo

if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "[crypto] Docker image not found: ${IMAGE_NAME}" >&2
  echo "[crypto] Build it first with: make build" >&2
  exit 1
fi

docker run --rm "$IMAGE_NAME" bash -lc '
  set -euo pipefail

  echo "=== OpenSSL version ==="
  openssl version -a
  echo

  echo "=== OpenSSL providers ==="
  openssl list -providers
  echo

  echo "=== KEM algorithms ==="
  openssl list -kem-algorithms 2>&1 || true
  echo

  echo "=== Signature algorithms ==="
  openssl list -signature-algorithms 2>&1 || true
  echo

  echo "=== Key exchange algorithms ==="
  openssl list -key-exchange-algorithms 2>&1 || true
  echo

  echo "=== Important PQC / hybrid entries ==="
  {
    openssl list -kem-algorithms 2>&1 || true
    openssl list -key-exchange-algorithms 2>&1 || true
    openssl list -signature-algorithms 2>&1 || true
  } | grep -Ei "ML-KEM|MLKEM|X25519MLKEM|X448MLKEM|SecP256r1MLKEM|SecP384r1MLKEM|ML-DSA|MLDSA|SLH-DSA|SLHDSA" || true
'