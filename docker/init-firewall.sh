#!/usr/bin/env bash
# Default-deny egress firewall for the Claude sandbox (runs as root from entrypoint.sh).
#
# Allows: loopback, DNS to the resolvers in /etc/resolv.conf, replies to allowed traffic, and a
# domain allowlist (+ GitHub's published CIDRs). Everything else outbound is rejected.
# Extra domains: EXTRA_ALLOWED_DOMAINS="host1.example host2.example" (space separated).
#
# Residual risks (see docs/decisions/0001-claude-sandbox.md): DNS to the configured resolver can still
# carry data out; allowed hosts (GitHub, PyPI, npm) can be abused as exfil channels; IPs are resolved
# once at start, so restart the container if a long session starts failing to reach the API.
set -euo pipefail

DOMAINS=(
  api.anthropic.com
  claude.ai
  console.anthropic.com
  platform.claude.com
  statsig.anthropic.com
  sentry.io
  registry.npmjs.org
  pypi.org
  files.pythonhosted.org
)
if [ -n "${EXTRA_ALLOWED_DOMAINS:-}" ]; then
  read -r -a EXTRA <<< "${EXTRA_ALLOWED_DOMAINS}"
  DOMAINS+=("${EXTRA[@]}")
fi

die() { echo "firewall: $*" >&2; exit 1; }

# 1. Keep Docker's embedded-DNS NAT rules across the flush.
DOCKER_DNS_RULES=$(iptables-save -t nat | grep -E '127\.0\.0\.11' || true)

iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
ipset destroy allowed-domains 2>/dev/null || true

if [ -n "$DOCKER_DNS_RULES" ]; then
  iptables -t nat -N DOCKER_OUTPUT 2>/dev/null || true
  iptables -t nat -N DOCKER_POSTROUTING 2>/dev/null || true
  echo "$DOCKER_DNS_RULES" | xargs -L 1 iptables -t nat
fi

# 2. Loopback and DNS (policy is still ACCEPT here, so resolution below works).
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
for ns in $(awk '/^nameserver/ {print $2}' /etc/resolv.conf | grep -E '^[0-9.]+$' || true); do
  iptables -A OUTPUT -p udp -d "$ns" --dport 53 -j ACCEPT
  iptables -A OUTPUT -p tcp -d "$ns" --dport 53 -j ACCEPT
done

# 3. Build the allowlist.
ipset create allowed-domains hash:net

gh_meta=$(curl -fsS --max-time 15 https://api.github.com/meta) || die "cannot fetch GitHub IP ranges"
echo "$gh_meta" | jq -e '.web and .api and .git' >/dev/null || die "unexpected GitHub meta response"
while read -r cidr; do
  [[ "$cidr" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}/[0-9]{1,2}$ ]] || continue   # IPv4 only
  ipset add -exist allowed-domains "$cidr"
done < <(echo "$gh_meta" | jq -r '(.web + .api + .git)[]')

for d in "${DOMAINS[@]}"; do
  ips=$(dig +short A "$d" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || true)
  if [ -z "$ips" ]; then
    echo "firewall: WARNING cannot resolve $d" >&2
    continue
  fi
  while read -r ip; do
    ipset add -exist allowed-domains "$ip"
  done <<< "$ips"
done

# 4. Rules and default-deny policies.
iptables -A INPUT  -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT
iptables -A OUTPUT -j REJECT --reject-with icmp-admin-prohibited
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# IPv6: no allowlist, just close it so it cannot bypass the IPv4 rules.
if command -v ip6tables >/dev/null 2>&1; then
  ip6tables -F 2>/dev/null || true
  ip6tables -A INPUT  -i lo -j ACCEPT 2>/dev/null || true
  ip6tables -A OUTPUT -o lo -j ACCEPT 2>/dev/null || true
  ip6tables -P INPUT DROP 2>/dev/null || true
  ip6tables -P FORWARD DROP 2>/dev/null || true
  ip6tables -P OUTPUT DROP 2>/dev/null || true
fi

# 5. Verify.
if curl -s --max-time 5 -o /dev/null https://example.com; then
  die "verification failed: example.com is reachable"
fi
curl -fsS --max-time 10 https://api.github.com/zen >/dev/null || die "verification failed: GitHub unreachable"
curl -s --max-time 10 -o /dev/null https://api.anthropic.com || die "verification failed: api.anthropic.com unreachable"

echo "firewall: egress allowlist active (${#DOMAINS[@]} domains + GitHub CIDRs)"
