#!/usr/bin/env bash
# Starts as root, installs the egress firewall, then drops to the unprivileged "dev" user.
# Capabilities (NET_ADMIN/NET_RAW) are granted to the container only so this script can run;
# gosu's uid change clears them for everything the user (and Claude) executes afterwards.
set -euo pipefail

if [ "$(id -u)" = "0" ]; then
  if [ "${SANDBOX_FIREWALL:-1}" = "1" ]; then
    /usr/local/bin/init-firewall.sh
  else
    echo "WARNING: SANDBOX_FIREWALL=0, egress firewall is DISABLED" >&2
  fi
  chown dev:dev /home/dev/.claude /home/dev/.ccache 2>/dev/null || true
  exec gosu dev "$@"
fi

exec "$@"
