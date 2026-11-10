# VPS bring-up (single environment)

Host: `135.148.219.175` (Ubuntu 26.04, 2 vCPU, 3.7 GiB RAM, 2 GB swap). Never the old shared server
`40.160.150.91` (`harden.sh` refuses to run there). Slave Kien runs these steps as `ubuntu` with sudo.

## 1. Harden (idempotent)

```sh
sudo bash deploy/bootstrap/harden.sh
```

## 2. Secrets, split per service (root, mode 600, values never in git or chat)

| File | Used by | Example |
|---|---|---|
| `/etc/kien/compose.env` | compose interpolation (no secrets) | `deploy/env-examples/compose.env.example` |
| `/etc/kien/postgres.env` | postgres | `deploy/env-examples/postgres.env.example` |
| `/etc/kien/migrate.env` | migrate (`kien_migrator`) | `deploy/env-examples/migrate.env.example` |
| `/etc/kien/app.env` | api, worker (`kien_app`, R2, Resend, session) | `deploy/env-examples/app.env.example` |
| `/etc/kien/ai.env` | ai-adapter (profile `ai`, off) | `deploy/env-examples/ai.env.example` |
| `/etc/kien/db-roles.env` | `bootstrap/db-roles.sh` | `KIEN_MIGRATOR_PASSWORD`, `KIEN_APP_PASSWORD`, `KIEN_BACKUP_PASSWORD` |
| `/etc/kien/restic.env`, `restic.pass`, `rclone.conf` | backups | `deploy/backup/restic.env.example` |

ClamAV and Caddy get no env file. Check: `sudo stat -c '%a %n' /etc/kien/*` shows `600` everywhere.

## 3. Build and deploy

```sh
sha=$(git rev-parse HEAD)                                   # on the box, from merged main
git archive --format=tar "$sha" | ssh ubuntu@135.148.219.175 "sudo mkdir -p /opt/kien/src/$sha && sudo tar -x -C /opt/kien/src/$sha"
sudo rsync -a --delete /opt/kien/src/$sha/deploy/ /opt/kien/deploy/
sudo /opt/kien/deploy/build-on-host.sh "$sha"               # prints kien-api:sha-<12>
sudo /opt/kien/deploy/deploy.sh "kien-api:sha-${sha:0:12}"  # prints the RELEASES.md row
```

`deploy.sh` order: pre-checks, backup if a migration is pending, record the previous image,
`up postgres`, db roles, `up clamav`, `run --rm migrate`, db roles again (grants on new tables),
`up --wait api worker caddy`, `ops/healthcheck.sh`.

## 4. Verify

```sh
curl -fsS --resolve api.kiensolutions.com:443:135.148.219.175 https://api.kiensolutions.com/health
sudo docker stats --no-stream; free -m
sudo /opt/kien/deploy/ops/healthcheck.sh
```

Caddy can only get a certificate once `api.kiensolutions.com` resolves to this host (DNS-only A
record). Before that, check the API inside the network:
`sudo docker compose -p kien --env-file /etc/kien/compose.env -f /opt/kien/deploy/docker-compose.prod.yml exec api python -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health').read())"`.

## 5. Timers and backups

```sh
sudo bash /opt/kien/deploy/bootstrap/install-timers.sh
sudo /opt/kien/deploy/backup/backup.sh && sudo /opt/kien/deploy/backup/restore-drill.sh
```

## Rollback

`sudo /opt/kien/deploy/rollback.sh` (previous image from `/opt/kien/releases/previous-image`).
Migrations are not reversed; restore a backup if the schema must go back.
