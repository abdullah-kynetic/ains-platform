#!/usr/bin/env bash
# Outbound rule for the AI service: its network (10.77.40.0/24) may reach openrouter.ai on 443 and
# DNS, and nothing else. Prints the rules by default; --apply installs them in DOCKER-USER (root).
# The adapter also refuses any other host in code (AI_ALLOWED_HOSTS); this is the network layer.
# IPv4 only: keep Docker IPv6 off for this network. To remove it, delete the DOCKER-USER jump, then the chain.
# The subnet is outside Docker's default pools on purpose, so no other stack can auto-receive it.
# Limitation: rules use the IPs openrouter.ai resolves to now. Re-run after any DNS change (it
# replaces its own rules). It never touches other networks, compose files or the server's deploy/ folder.
set -euo pipefail
SUBNET="10.77.40.0/24"
HOST="openrouter.ai"
CHAIN="KIEN-AI-EGRESS"
APPLY=0
[ "${1:-}" = "--apply" ] && APPLY=1

mapfile -t IPS < <(getent ahostsv4 "$HOST" | awk '{print $1}' | sort -u)
[ "${#IPS[@]}" -gt 0 ] || { echo "cannot resolve $HOST" >&2; exit 1; }

# DNS only to the host's own resolvers (never to any address). Skips loopback stubs.
RESOLV=/etc/resolv.conf
[ -r /run/systemd/resolve/resolv.conf ] && RESOLV=/run/systemd/resolve/resolv.conf
mapfile -t NS < <(awk '/^nameserver/ && $2 ~ /^[0-9.]+$/ && $2 !~ /^127\./ {print $2}' "$RESOLV")
[ "${#NS[@]}" -gt 0 ] || { echo "no usable resolver in $RESOLV" >&2; exit 1; }

rules=()
rules+=("-N $CHAIN")
rules+=("-F $CHAIN")
for ns in "${NS[@]}"; do
  rules+=("-A $CHAIN -p udp -d $ns --dport 53 -j ACCEPT")
  rules+=("-A $CHAIN -p tcp -d $ns --dport 53 -j ACCEPT")
done
for ip in "${IPS[@]}"; do rules+=("-A $CHAIN -p tcp -d $ip --dport 443 -j ACCEPT"); done
rules+=("-A $CHAIN -j DROP")

if [ "$APPLY" = 0 ]; then
  echo "# dry run. Resolved $HOST -> ${IPS[*]}"
  printf 'iptables %s\n' "${rules[@]}"
  echo "iptables -D DOCKER-USER -s $SUBNET -j $CHAIN   # if present, then:"
  echo "iptables -I DOCKER-USER -s $SUBNET -j $CHAIN"
  echo "# Re-run with --apply (as root) to install."
  exit 0
fi
[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 1; }
iptables -N "$CHAIN" 2>/dev/null || true
iptables -F "$CHAIN"
for r in "${rules[@]:2}"; do iptables $r; done
iptables -D DOCKER-USER -s "$SUBNET" -j "$CHAIN" 2>/dev/null || true
iptables -I DOCKER-USER -s "$SUBNET" -j "$CHAIN"
echo "installed: $SUBNET may reach $HOST (${IPS[*]}) on 443 and DNS via ${NS[*]} only"
