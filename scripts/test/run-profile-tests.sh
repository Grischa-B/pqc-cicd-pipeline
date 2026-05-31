#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <profile>" >&2
  exit 2
fi

PROFILE="$1"

"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run-handshake-test.sh" "$PROFILE"