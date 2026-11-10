#!/usr/bin/env bash
# Idempotent host hardening for the Kien VPS (Ubuntu 24.04+ / 26.04). Run as root.
# Live host: 135.148.219.175. Refuses to run on the old shared server 40.160.150.91.
set -euo pipefail
FORBIDDEN_IP=40.160.150.91
public_ip=${KIEN_PUBLIC_IP:-$(curl -fsS -m 10 https://api.ipify.org || true)}
local_ips=$(hostname -I 2>/dev/null || true)
case " $public_ip $local_ips " in
  *" $FORBIDDEN_IP "*) echo "refusing to run: this is the old shared server $FORBIDDEN_IP" >&2; exit 3 ;;
esac
[ "$(id -u)" = 0 ] || { echo "run as root" >&2; exit 2; }
. /etc/os-release
[ "$ID" = ubuntu ] || { echo "Ubuntu only" >&2; exit 2; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -yq ufw fail2ban unattended-upgrades chrony ca-certificates curl gnupg restic rclone

for u in kien kien-deploy; do
  id "$u" >/dev/null 2>&1 || useradd -m -s /bin/bash "$u"
  install -d -m 700 -o "$u" -g "$u" "/home/$u/.ssh"
  touch "/home/$u/.ssh/authorized_keys"; chown "$u:$u" "/home/$u/.ssh/authorized_keys"
  chmod 600 "/home/$u/.ssh/authorized_keys"
done

cat > /etc/ssh/sshd_config.d/00-kien-hardening.conf <<'CONF'
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
CONF
sshd -t && systemctl reload ssh

ufw default deny incoming
ufw default allow outgoing
ufw limit 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

systemctl enable --now fail2ban unattended-upgrades chrony

if ! swapon --show | grep -q /swapfile; then
  [ -f /swapfile ] || { fallocate -l 2G /swapfile; chmod 600 /swapfile; mkswap /swapfile; }
  swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -q
  apt-get install -yq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
mkdir -p /etc/docker
[ -f /etc/docker/daemon.json ] || echo '{"no-new-privileges": true, "live-restore": true, "log-driver": "local"}' > /etc/docker/daemon.json
systemctl enable --now docker

install -d -m 700 -o root -g root /etc/kien /opt/kien
for d in src releases deploy backups data evidence; do install -d -m 700 -o root -g root "/opt/kien/$d"; done
echo "harden ok"
