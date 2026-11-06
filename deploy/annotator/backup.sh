#!/usr/bin/env bash
# Run as root; local backups must also be copied to encrypted off-host storage.
set -euo pipefail
umask 077
exec 9>/run/lock/vectofit-backup.lock
flock -n 9 || exit 1
backup_dir="/var/backups/vectofit/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
# Block writes while capturing matching database and media snapshots.
trap 'systemctl start vectofit-web vectofit-worker' EXIT
systemctl stop vectofit-web vectofit-worker
runuser -u postgres -- pg_dump --format=custom vectofit > "$backup_dir/database.dump"
tar -C /srv/vectofit/data -czf "$backup_dir/media.tar.gz" media
cp /etc/vectofit/backend.env "$backup_dir/backend.env"
(
    cd "$backup_dir"
    sha256sum database.dump media.tar.gz > SHA256SUMS
)
touch "$backup_dir/COMPLETE"
