#!/bin/bash
# Runs once, as root, when the server first boots (EC2 user data). Installs Docker and
# makes the folder deploy.sh uses. Nothing else lives here on purpose: deploy.sh uploads
# update.sh and the Caddyfile (from deploy/templates/) on every deploy, so they never
# go stale on a server that has been running for a while.
set -euxo pipefail

dnf install -y docker
systemctl enable --now docker

mkdir -p /opt/pixeltrip
chmod 700 /opt/pixeltrip
