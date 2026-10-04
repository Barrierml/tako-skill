#!/usr/bin/env bash
set -euo pipefail

# Install the sync job on the mirror host. Run only after the production mirror
# host, domain and stack have passed review.
ROOT="${TAKO_SKILL_MIRROR_ROOT:-/srv/tako-skill-mirror}"
install -d -m 0755 "$ROOT" /usr/local/libexec /etc/systemd/system
install -m 0755 "$(dirname "$0")/sync.sh" /usr/local/libexec/tako-skill-mirror-sync
install -m 0644 "$(dirname "$0")/tako-skill-mirror-sync.service" /etc/systemd/system/
install -m 0644 "$(dirname "$0")/tako-skill-mirror-sync.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now tako-skill-mirror-sync.timer
systemctl start tako-skill-mirror-sync.service
