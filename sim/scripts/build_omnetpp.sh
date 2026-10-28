#!/usr/bin/env bash
# Build the socket bridge (sim/bridge) as a shared library against INET (paths from the environment).
# Simu5G is linked from stage 3 on. Usage: sim/scripts/build_omnetpp.sh [release|debug]
set -euo pipefail
if [ -z "${OMNETPP_ROOT:-}" ] || [ -z "${INET_ROOT:-}" ]; then
    echo "OMNETPP_ROOT/INET_ROOT not set: run this inside the container (make shell), not on the host." >&2
    exit 1
fi
mode="${1:-release}"
cd "$(dirname "$0")/../bridge"
command -v opp_makemake >/dev/null || { echo "opp_makemake not on PATH (image sets it)" >&2; exit 1; }
opp_makemake -f --deep --make-so -o linklossbridge -O out \
    -I"$INET_ROOT/src" -L"$INET_ROOT/src" -lINET\$\(D\) -DINET_IMPORT
make -j"$(nproc)" MODE="$mode"
