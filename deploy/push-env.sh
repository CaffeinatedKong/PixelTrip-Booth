#!/usr/bin/env bash
# Upload the backend's settings from backend/.env to AWS Parameter Store, encrypted.
# The server reads them on every deploy. Values are never printed.
#
# Run again whenever a key changes, then ./deploy/deploy.sh --restart to apply it.
# The upload mirrors the file: a key removed from backend/.env (or left empty) is deleted
# from Parameter Store too, so a retired secret does not live on in production.
# A value that spans several lines (a private key) cannot be passed to the container, so
# this stops with the line number instead of uploading a corrupted value.
#
# Local-only settings are replaced with production ones:
#   FRONTEND_URL          -> $FRONTEND_ORIGIN (the deployed frontend)
#   ENVIRONMENT           -> production
#   ENABLE_DEV_ENDPOINTS  -> false (the /dev test routes stay off)

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./config.sh

ENV_FILE="${1:-../backend/.env}"
[ -f "$ENV_FILE" ] || { echo "No $ENV_FILE to read." >&2; exit 1; }

SENT=" "   # space-separated names uploaded this run

put() {  # name value
  aws ssm put-parameter --name "${PARAM_PATH}/$1" --value "$2" \
    --type SecureString --overwrite >/dev/null
  SENT+="$1 "
  echo "  set $1"
}

# Refuse the whole upload before changing anything if the file has a multi-line value.
lineno=0
while IFS= read -r line || [ -n "$line" ]; do
  lineno=$((lineno + 1))
  case "$line" in ''|\#*) continue ;; esac
  value="${line#*=}"
  if [ "$value" = "$line" ]; then
    echo "$ENV_FILE line $lineno has no '=': multi-line values are not supported." >&2
    exit 1
  fi
  # An opening quote with no closing one means the value continues on the next line.
  case "$value" in
    \"*) [ "${#value}" -ge 2 ] && [ "${value%\"}" != "$value" ] || bad=1 ;;
    \'*) [ "${#value}" -ge 2 ] && [ "${value%\'}" != "$value" ] || bad=1 ;;
  esac
  if [ "${bad:-0}" = 1 ]; then
    echo "$ENV_FILE line $lineno: a quoted value is not closed on the same line." >&2
    echo "Multi-line values cannot be passed to the container; put it on one line." >&2
    exit 1
  fi
done < "$ENV_FILE"

echo "==> Uploading settings to ${PARAM_PATH} in ${AWS_REGION}"
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in ''|\#*) continue ;; esac
  key="${line%%=*}"
  value="${line#*=}"
  key="$(echo "$key" | tr -d '[:space:]')"
  # Drop surrounding quotes, as dotenv does.
  value="${value%\"}"; value="${value#\"}"; value="${value%\'}"; value="${value#\'}"
  case "$key" in
    HOST|PORT|APP_ENV|ENVIRONMENT|FRONTEND_URL|ENABLE_DEV_ENDPOINTS) continue ;;
  esac
  [ -n "$value" ] || continue   # Parameter Store refuses empty values; unset means default
  put "$key" "$value"
done < "$ENV_FILE"

put FRONTEND_URL "$FRONTEND_ORIGIN"
put ENVIRONMENT production
put ENABLE_DEV_ENDPOINTS false

echo "==> Removing settings that are no longer in ${ENV_FILE}"
STALE=()
for name in $(aws ssm get-parameters-by-path --path "$PARAM_PATH" \
    --query 'Parameters[].Name' --output text); do
  key="${name##*/}"
  case "$SENT" in *" $key "*) ;; *) STALE+=("$name") ;; esac
done
if [ "${#STALE[@]}" -eq 0 ]; then
  echo "  nothing to remove"
else
  for ((i = 0; i < ${#STALE[@]}; i += 10)) ; do   # the API takes 10 names at a time
    aws ssm delete-parameters --names "${STALE[@]:i:10}" >/dev/null
  done
  for name in "${STALE[@]}"; do echo "  removed ${name##*/}"; done
fi

echo "Done. Apply with: ./deploy/deploy.sh --restart"
