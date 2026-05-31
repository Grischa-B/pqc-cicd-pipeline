#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <profile>" >&2
  exit 2
fi

PROFILE="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROFILE_FILE="$ROOT_DIR/configs/profiles/${PROFILE}.yml"

if [[ ! -f "$PROFILE_FILE" ]]; then
  echo "[certs] Profile not found: $PROFILE_FILE" >&2
  exit 1
fi

yaml_value() {
  local key="$1"
  local file="$2"

  awk -F': *' -v key="$key" '
    {
      k=$1
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", k)
      if (k == key) {
        v=$2
        gsub(/^[[:space:]"]+|[[:space:]"]+$/, "", v)
        print v
        exit
      }
    }
  ' "$file"
}

KEY_TYPE="$(yaml_value "key_type" "$PROFILE_FILE")"
CURVE="$(yaml_value "curve" "$PROFILE_FILE")"

if [[ -z "$KEY_TYPE" ]]; then
  echo "[certs] key_type is empty in $PROFILE_FILE" >&2
  exit 1
fi

if [[ "$KEY_TYPE" != "ec" ]]; then
  echo "[certs] Only EC certificates are implemented at this stage. profile=$PROFILE key_type=$KEY_TYPE" >&2
  exit 1
fi

if [[ -z "$CURVE" ]]; then
  CURVE="prime256v1"
fi

cd "$ROOT_DIR"

CERT_DIR="artifacts/certs/${PROFILE}"
LOG_DIR="artifacts/logs/${PROFILE}"

rm -rf "$CERT_DIR"
mkdir -p "$CERT_DIR" "$LOG_DIR"

echo "[certs] Generating certificates for profile=$PROFILE curve=$CURVE"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$ROOT_DIR:/workspace" \
  -w /workspace \
  pqc-crypto-base:local \
  bash -lc "
    set -euo pipefail

    CERT_DIR='artifacts/certs/${PROFILE}'
    LOG_FILE='artifacts/logs/${PROFILE}/cert-generation.log'

    {
      echo '[certs] OpenSSL version:'
      openssl version -a
      echo

      echo '[certs] Generating EC CA key...'
      openssl ecparam -name '${CURVE}' -genkey -noout -out \"\$CERT_DIR/ca.key\"

      echo '[certs] Generating self-signed CA certificate...'
      openssl req -x509 -new -key \"\$CERT_DIR/ca.key\" \
        -sha256 \
        -days 7 \
        -subj '/CN=PQC Test CA ${PROFILE}' \
        -out \"\$CERT_DIR/ca.crt\"

      echo '[certs] Generating server EC key...'
      openssl ecparam -name '${CURVE}' -genkey -noout -out \"\$CERT_DIR/server.key\"

      echo '[certs] Generating server CSR...'
      openssl req -new -key \"\$CERT_DIR/server.key\" \
        -subj '/CN=localhost' \
        -out \"\$CERT_DIR/server.csr\"

      cat > \"\$CERT_DIR/server.ext\" <<'CERT_EOF'
subjectAltName=DNS:localhost,DNS:tls-server,IP:127.0.0.1
extendedKeyUsage=serverAuth
keyUsage=digitalSignature
CERT_EOF

      echo '[certs] Signing server certificate...'
      openssl x509 -req \
        -in \"\$CERT_DIR/server.csr\" \
        -CA \"\$CERT_DIR/ca.crt\" \
        -CAkey \"\$CERT_DIR/ca.key\" \
        -CAcreateserial \
        -out \"\$CERT_DIR/server.crt\" \
        -days 7 \
        -sha256 \
        -extfile \"\$CERT_DIR/server.ext\"

      echo '[certs] Certificate details:'
      openssl x509 -in \"\$CERT_DIR/server.crt\" -noout -subject -issuer -dates
      openssl x509 -in \"\$CERT_DIR/server.crt\" -noout -text > \"\$CERT_DIR/server-cert-details.txt\"

      echo '[certs] Generated files:'
      find \"\$CERT_DIR\" -maxdepth 1 -type f -printf '%f %s bytes\n' | sort
    } > \"\$LOG_FILE\" 2>&1
  "

echo "[certs] Certificates generated in $CERT_DIR"
echo "[certs] Log: $LOG_DIR/cert-generation.log"