#!/usr/bin/env bash
# Exercises templates/update.sh against fake `docker` and `aws` commands: no AWS, no
# Docker. Run:  ./deploy/tests/update_sh_test.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT
FAILS=0

mkdir -p "$ROOT/bin" "$ROOT/state/containers" "$ROOT/dir"
export STATE="$ROOT/state" PIXELTRIP_DIR="$ROOT/dir" PARAMS_JSON="$ROOT/params.json"
export HEALTH_TRIES=2 HEALTH_WAIT=0
export PATH="$ROOT/bin:$PATH"

# --- fakes -------------------------------------------------------------------------------
cat > "$ROOT/bin/docker" <<'FAKE'
#!/usr/bin/env bash
echo "docker $*" >> "$STATE/log"
C="$STATE/containers"
case "$1" in
  inspect)
    name="${@: -1}"
    [ -f "$C/$name" ] || exit 1
    case "$*" in *Config.Image*) cat "$C/$name" ;; esac ;;
  ps) ls "$C" ;;
  run)
    name=""; prev=""
    for a in "$@"; do [ "$prev" = "--name" ] && name="$a"; prev="$a"; done
    echo "${@: -1}" > "$C/$name" ;;
  exec)
    name="$2"
    [ "$name" = caddy ] && exit 0
    grep -q ':bad$' "$C/$name" 2>/dev/null && exit 1
    [ -f "$C/$name" ] ;;
  rename) mv "$C/$2" "$C/$3" ;;
  rm) for a in "$@"; do [ -f "$C/$a" ] && rm -f "$C/$a"; done; exit 0 ;;
  *) exit 0 ;;
esac
FAKE
cat > "$ROOT/bin/aws" <<'FAKE'
#!/usr/bin/env bash
case "$*" in
  *get-parameters-by-path*) cat "$PARAMS_JSON" ;;
  *get-login-password*) echo password ;;
esac
FAKE
chmod +x "$ROOT/bin/docker" "$ROOT/bin/aws"

sed -e 's|__REGION__|ap-southeast-1|g' -e 's|__REGISTRY__|123.dkr.ecr.test|g' \
    -e 's|__APP_NAME__|app|g' -e 's|__PARAM_PATH__|/p|g' \
    "$HERE/../templates/update.sh" > "$ROOT/update.sh"
chmod +x "$ROOT/update.sh"

params() { printf '{"Parameters":[{"Name":"/p/KEY","Value":"%s"}]}' "$1" > "$PARAMS_JSON"; }
image_of() { cat "$STATE/containers/$1" 2>/dev/null || echo "(none)"; }
has() { [ -f "$STATE/containers/$1" ]; }
check() {  # description, condition-exit-status
  if [ "$2" -eq 0 ]; then echo "ok   - $1"; else echo "FAIL - $1"; FAILS=$((FAILS + 1)); fi
}
deploy() { "$ROOT/update.sh" "$@" >"$ROOT/out" 2>&1; }

params secret

deploy v1
check "first deploy starts the backend on v1" "$([ "$(image_of backend)" = 123.dkr.ecr.test/app:v1 ]; echo $?)"
check "first deploy leaves no temporary containers" "$(! has backend-new && ! has backend-old; echo $?)"
check "first deploy starts caddy" "$(has caddy; echo $?)"

deploy v2
check "a healthy update switches to v2" "$([ "$(image_of backend)" = 123.dkr.ecr.test/app:v2 ]; echo $?)"
check "the old container is removed afterwards" "$(! has backend-old && ! has backend-new; echo $?)"

deploy bad; status=$?
check "an unhealthy update fails" "$([ "$status" -ne 0 ]; echo $?)"
check "the previous version is still running after a failed update" \
  "$([ "$(image_of backend)" = 123.dkr.ecr.test/app:v2 ]; echo $?)"
check "the failed candidate is cleaned up" "$(! has backend-new; echo $?)"

deploy current
check "'current' restarts the image already running" \
  "$([ "$(image_of backend)" = 123.dkr.ecr.test/app:v2 ]; echo $?)"

printf 'new-host.example {\n}\n' > "$ROOT/dir/Caddyfile.new"
: > "$STATE/log"
deploy v2
check "a changed Caddyfile is installed" "$(grep -q new-host "$ROOT/dir/Caddyfile"; echo $?)"
check "a changed Caddyfile triggers a reload" "$(grep -q 'caddy reload' "$STATE/log"; echo $?)"
check "Caddyfile.new is cleaned up" "$([ ! -f "$ROOT/dir/Caddyfile.new" ]; echo $?)"

cp "$ROOT/dir/Caddyfile" "$ROOT/dir/Caddyfile.new"
: > "$STATE/log"
deploy v2
check "an unchanged Caddyfile is not reloaded" "$(! grep -q 'caddy reload' "$STATE/log"; echo $?)"

printf '{"Parameters":[{"Name":"/p/PRIVATE_KEY","Value":"line1\\nline2"}]}' > "$PARAMS_JSON"
before="$(image_of backend)"
deploy v3; status=$?
check "a multi-line setting stops the deploy" "$([ "$status" -ne 0 ]; echo $?)"
check "the error names the key" "$(grep -q PRIVATE_KEY "$ROOT/out"; echo $?)"
check "the error does not print the value" "$(! grep -q line2 "$ROOT/out"; echo $?)"
check "nothing was changed by the refused deploy" "$([ "$(image_of backend)" = "$before" ]; echo $?)"

[ "$FAILS" -eq 0 ] && echo "all passed" || { echo "$FAILS failed"; exit 1; }
