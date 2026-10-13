#!/bin/bash
# Start or update the backend on this server. Run as root; deploy.sh uploads and runs it
# on EVERY deploy (through Systems Manager), so edits to this file and to the Caddyfile
# reach a server that has already been running for months.
#
#   update.sh <tag>      deploy that image tag
#   update.sh current    restart the image that is running now, with fresh settings
#
# The old container keeps serving until the new one answers its health check, so a bad
# image or bad settings leave the last good version running instead of nothing.
set -euo pipefail

REGION="__REGION__"
REGISTRY="__REGISTRY__"
APP="__APP_NAME__"
PARAM_PATH="__PARAM_PATH__"
DIR="${PIXELTRIP_DIR:-/opt/pixeltrip}"
ENV_FILE="$DIR/backend.env"
CADDYFILE="$DIR/Caddyfile"
CADDY_NEW="$DIR/Caddyfile.new"
HEALTH_TRIES="${HEALTH_TRIES:-30}"
HEALTH_WAIT="${HEALTH_WAIT:-2}"

ARG="${1:-current}"
if [ "$ARG" = "current" ]; then
  IMAGE="$(docker inspect --format '{{.Config.Image}}' backend 2>/dev/null || true)"
  [ -n "$IMAGE" ] || { echo "No running backend to restart; pass an image tag." >&2; exit 1; }
else
  IMAGE="${REGISTRY}/${APP}:${ARG}"
fi

# --- Settings: Parameter Store -> a root-only env file ---------------------------------
# docker's env-file format has no way to hold a newline, so a multi-line value (a private
# key, say) would be silently cut apart. Refuse it, naming the key, instead.
umask 077
aws ssm get-parameters-by-path --region "$REGION" --path "$PARAM_PATH" \
  --with-decryption --output json |
  python3 -c '
import json, sys
bad = []
for p in json.load(sys.stdin)["Parameters"]:
    key = p["Name"].rsplit("/", 1)[-1]
    if "\n" in p["Value"] or "\r" in p["Value"]:
        bad.append(key)
        continue
    print(key + "=" + p["Value"])
if bad:
    sys.stderr.write("Settings with a line break cannot be passed to the container: " + ", ".join(bad) + "\n")
    sys.exit(3)
' > "${ENV_FILE}.new"
if [ ! -s "${ENV_FILE}.new" ]; then
  rm -f "${ENV_FILE}.new"
  echo "No settings found under ${PARAM_PATH}. Run deploy/push-env.sh first." >&2
  exit 1
fi
mv "${ENV_FILE}.new" "$ENV_FILE"

# --- Image -----------------------------------------------------------------------------
aws ecr get-login-password --region "$REGION" |
  docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
docker pull "$IMAGE"
docker network inspect pixeltrip >/dev/null 2>&1 || docker network create pixeltrip

healthy() {  # container name
  local _
  for _ in $(seq 1 "$HEALTH_TRIES"); do
    if docker exec "$1" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" 2>/dev/null; then
      return 0
    fi
    sleep "$HEALTH_WAIT"
  done
  return 1
}

# --- Start the new version beside the old one, and switch only if it is healthy ---------
docker rm -f backend-new >/dev/null 2>&1 || true
docker run -d --name backend-new --network pixeltrip --restart unless-stopped \
  --env-file "$ENV_FILE" \
  --log-opt max-size=10m --log-opt max-file=5 \
  "$IMAGE" >/dev/null

if ! healthy backend-new; then
  echo "The new backend did not become healthy; the previous version was left running." >&2
  docker logs --tail 40 backend-new >&2 || true
  docker rm -f backend-new >/dev/null 2>&1 || true
  exit 1
fi

had_old=0
if docker inspect backend >/dev/null 2>&1; then
  had_old=1
  docker rename backend backend-old
  docker stop backend-old >/dev/null
fi
docker rename backend-new backend
# The proxy reaches the app by the name "backend": make that name point at the new one.
docker network disconnect pixeltrip backend >/dev/null 2>&1 || true
docker network connect --alias backend pixeltrip backend

if ! healthy backend; then
  echo "The new backend failed after the switch; rolling back." >&2
  docker logs --tail 40 backend >&2 || true
  docker rm -f backend >/dev/null 2>&1 || true
  if [ "$had_old" = 1 ]; then
    docker rename backend-old backend
    docker start backend >/dev/null
  fi
  exit 1
fi
docker rm -f backend-old >/dev/null 2>&1 || true

# --- Caddy (HTTPS in front): keep its config in step with the one deploy.sh sent ---------
changed=0
if [ -f "$CADDY_NEW" ]; then
  if ! cmp -s "$CADDY_NEW" "$CADDYFILE" 2>/dev/null; then
    # Rewrite in place: the container mounts this file, and a new file would be a new inode.
    cat "$CADDY_NEW" > "$CADDYFILE"
    changed=1
  fi
  rm -f "$CADDY_NEW"
fi
if ! docker ps --format '{{.Names}}' | grep -qx caddy; then
  docker rm -f caddy >/dev/null 2>&1 || true
  docker run -d --name caddy --network pixeltrip --restart unless-stopped \
    -p 80:80 -p 443:443 -p 443:443/udp \
    -v "$CADDYFILE":/etc/caddy/Caddyfile:ro \
    -v caddy_data:/data -v caddy_config:/config \
    --log-opt max-size=10m --log-opt max-file=3 \
    caddy:2 >/dev/null
elif [ "$changed" = 1 ]; then
  if ! docker exec caddy caddy reload --config /etc/caddy/Caddyfile; then
    echo "Caddy rejected the new config. The backend is up, but check $CADDYFILE." >&2
    exit 1
  fi
  echo "Caddy config reloaded."
fi

docker image prune -f >/dev/null
echo "Backend is up: $IMAGE"
