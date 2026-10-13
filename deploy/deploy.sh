#!/usr/bin/env bash
# Deploy the backend: build the image, push it to ECR, restart it on the server.
#
#   ./deploy/deploy.sh                 build from backend/ and deploy (backend/ must be committed)
#   ./deploy/deploy.sh --allow-dirty   ship uncommitted backend/ changes under a unique tag
#   ./deploy/deploy.sh --restart       no build: restart the running image with fresh settings
#
# The image is tagged with the git commit (immutable in ECR). The server starts the new
# version beside the old one and only switches once it answers its health check.
#
# Needs: Docker running, and the AWS CLI logged in. Run aws-setup.sh and push-env.sh first.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

INSTANCE_ID="$(instance_id)"
[ -n "$INSTANCE_ID" ] || { echo "No server found. Run ./deploy/aws-setup.sh first." >&2; exit 1; }
HOST="$(backend_host)"
REGISTRY="$(ecr_registry)"

MODE=build
ALLOW_DIRTY=0
for arg in "$@"; do
  case "$arg" in
    --restart) MODE=restart ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [ "$MODE" = restart ]; then
  TAG=current   # keep the image that is running; only the settings are refreshed
else
  SHA="$(git rev-parse --short HEAD 2>/dev/null || true)"
  [ -n "$SHA" ] || { echo "Not a git checkout: cannot name the image." >&2; exit 1; }
  if [ -n "$(git status --porcelain ../backend 2>/dev/null)" ]; then
    if [ "$ALLOW_DIRTY" != 1 ]; then
      echo "backend/ has uncommitted changes. An image tagged ${SHA} would not match that" >&2
      echo "commit. Commit them, or pass --allow-dirty to ship them under a unique tag." >&2
      exit 1
    fi
    TAG="${SHA}-dirty-$(date +%Y%m%d%H%M%S)"
  else
    TAG="$SHA"
  fi
  # Tags are immutable in ECR, so an image that is already there is reused as it is.
  if aws ecr describe-images --repository-name "$APP_NAME" \
      --image-ids "imageTag=${TAG}" >/dev/null 2>&1; then
    echo "==> ${APP_NAME}:${TAG} is already in ECR; not rebuilding"
  else
    echo "==> Building ${APP_NAME}:${TAG} for ARM and pushing to ECR"
    aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
    docker buildx build --platform linux/arm64 \
      -t "${REGISTRY}/${APP_NAME}:${TAG}" --push ../backend
  fi
fi

# update.sh and the Caddyfile are sent on every deploy, so a change to either (a new
# elastic IP means a new sslip.io hostname, say) reaches a server that is already running.
render() {
  sed -e "s|__REGION__|${AWS_REGION}|g" -e "s|__REGISTRY__|${REGISTRY}|g" \
      -e "s|__APP_NAME__|${APP_NAME}|g" -e "s|__PARAM_PATH__|${PARAM_PATH}|g" \
      -e "s|__HOST__|${HOST}|g" "$1"
}
UPDATE_B64="$(render templates/update.sh | base64 | tr -d '\n')"
CADDY_B64="$(render templates/Caddyfile | base64 | tr -d '\n')"
PARAMS_FILE="$(mktemp)"
trap 'rm -f "$PARAMS_FILE"' EXIT
python3 - "$UPDATE_B64" "$CADDY_B64" "$TAG" > "$PARAMS_FILE" <<'PY'
import json, sys

update_b64, caddy_b64, tag = sys.argv[1:4]
print(json.dumps({"commands": [
    "set -e",
    "mkdir -p /opt/pixeltrip",
    f"echo {update_b64} | base64 -d > /opt/pixeltrip/update.sh",
    "chmod 700 /opt/pixeltrip/update.sh",
    f"echo {caddy_b64} | base64 -d > /opt/pixeltrip/Caddyfile.new",
    f"/opt/pixeltrip/update.sh {tag}",
]}))
PY

echo "==> Updating the backend on ${INSTANCE_ID} (${TAG})"
COMMAND_ID="$(aws ssm send-command --instance-ids "$INSTANCE_ID" \
  --document-name AWS-RunShellScript --comment "deploy ${APP_NAME}:${TAG}" \
  --parameters "file://${PARAMS_FILE}" \
  --query Command.CommandId --output text)"
STATUS=Pending
for _ in $(seq 1 90); do   # up to 6 minutes: the first pull is the slow one
  sleep 4
  STATUS="$(aws ssm get-command-invocation --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" --query Status --output text 2>/dev/null || echo Pending)"
  case "$STATUS" in Pending|InProgress|Delayed) ;; *) break ;; esac
done
aws ssm get-command-invocation --command-id "$COMMAND_ID" --instance-id "$INSTANCE_ID" \
  --query '[StandardOutputContent, StandardErrorContent]' --output text | tail -n 25
[ "$STATUS" = "Success" ] || { echo "Deploy failed (${STATUS}); the previous version is still serving." >&2; exit 1; }

echo "==> Checking https://${HOST}/health"
for _ in $(seq 1 20); do
  if curl -fsS --max-time 5 "https://${HOST}/health" >/dev/null 2>&1; then
    echo "Live: https://${HOST}"
    exit 0
  fi
  sleep 3   # the first deploy waits for Caddy to get its certificate
done
echo "The container is running but https://${HOST}/health did not answer yet." >&2
echo "On a first deploy the certificate can take a minute; try the URL again shortly." >&2
exit 1
