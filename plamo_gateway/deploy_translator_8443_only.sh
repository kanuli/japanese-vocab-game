#!/bin/sh
# Translator ONLY: activate already-proven PLaMo route on EXISTING HTTPS 8443.
# Does not edit vocabulary/conjugation/audio code, database, frontend or Nginx.
# Docker Compose recreates ONLY japanese-api (brief shared-API interruption).
# Failed public checks automatically recreate the original image (rollback).
set -eu
umask 077
ROOT="/volume2/docker/japanese-api"
DOCKER="/usr/local/bin/docker"
BASE="$ROOT/compose.yaml"
CANDIDATE="japanese-api:plamo-8443-20261112_141623"
SOCKDIR="$HOME/plamo-gateway-run"
BACKUP="$HOME/japanese-api-rollbacks/preplamo-20261112_130956"
WORK="$HOME/plamo-translation-deploy-$(date +%Y%m%d_%H%M%S)"
DEployed=0
COMMITTED=0

rollback() {
    rc=$?
    trap - EXIT HUP INT TERM
    if [ "$DEployed" = 1 ] && [ "$COMMITTED" != 1 ]; then
        echo "AUTOMATIC_ROLLBACK=START"
        if sudo "$DOCKER" compose -p "$PROJECT" -f "$BASE" -f "$WORK/rollback.override.yaml" \
            up -d --no-deps --no-build japanese-api; then
            echo "AUTOMATIC_ROLLBACK=COMPLETE"
        else
            echo "AUTOMATIC_ROLLBACK=FAILED_MANUAL_ACTION_REQUIRED"
            echo "ROLLBACK_SCRIPT=$WORK/rollback.sh"
        fi
    fi
    exit "$rc"
}
trap rollback EXIT
echo "=== TRANSLATOR PLaMo: SINGLE SERVICE 8443 CUTOVER ==="

# Read-only preflight, *before* any service image change.
test -f "$BASE" && test -f "$BACKUP/api-source.tar.gz" && test -f "$BACKUP/image-id.txt"
test -d "$SOCKDIR" && test ! -L "$SOCKDIR" && test -S "$SOCKDIR/gateway.sock"
test -x "$DOCKER"
expected=$(tar -xOzf "$BACKUP/api-source.tar.gz" app/main.py | sha256sum | awk '{print $1}')
actual=$(sha256sum "$ROOT/app/main.py" | awk '{print $1}')
if [ "$expected" != "$actual" ]; then
    echo "MAIN_SOURCE_CHANGED=STOP"; exit 4
fi
echo "UNCHANGED_PRODUCTION_SOURCE=PASS"

# Validate private Shadow Gateway UDS without credentials.
python3 - "$SOCKDIR/gateway.sock" <<'PY'
import os,socket,stat,sys
p=sys.argv[1]
d=os.stat(os.path.dirname(p), follow_symlinks=False)
s=os.stat(p, follow_symlinks=False)
if not stat.S_ISSOCK(s.st_mode) or d.st_mode & 0o777 != 0o700 or s.st_mode & 0o777 != 0o600:
    raise SystemExit("PRIVATE_UDS_MODE=FAIL")
sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
sock.settimeout(5)
try:
    sock.connect(p)
    sock.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    data=sock.recv(1024)
finally:
    sock.close()
if not (b"HTTP/1.0 200" in data or b"HTTP/1.1 200" in data):
    raise SystemExit("PRIVATE_UDS_HEALTH=FAIL")
print("PRIVATE_UDS_HEALTH=PASS")
PY

sudo "$DOCKER" compose version >/dev/null
PROJECT=$(sudo "$DOCKER" inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' japanese-api)
SERVICE=$(sudo "$DOCKER" inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' japanese-api)
case "$PROJECT" in ''|*[^a-zA-Z0-9_-]*) echo "UNKNOWN_COMPOSE_PROJECT=STOP"; exit 5 ;; esac
test "$SERVICE" = japanese-api || { echo "SERVICE_LABEL_MISMATCH=STOP"; exit 5; }
USER_ID=$(sudo "$DOCKER" inspect --format '{{.Config.User}}' japanese-api)
case "$USER_ID" in ''|'0'|'0:0'|'root') ;; *) echo "NONROOT_SERVICE_SOCKET_ACCESS_UNVERIFIED=STOP"; exit 5 ;; esac
ORIGINAL=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
test "$ORIGINAL" = "$(cat "$BACKUP/image-id.txt")" || {
    echo "ORIGINAL_IMAGE_DIFFERS_FROM_BACKUP=STOP"; exit 5;
}
sudo "$DOCKER" image inspect "$CANDIDATE" >/dev/null
echo "CANDIDATE_AND_ORIGINAL_IMAGES=PASS"

# Verify existing public reverse proxy is healthy BEFORE changing the service.
PUBLIC="https://kanu-rustdesk.synology.me:8443"
RESOLVE="kanu-rustdesk.synology.me:8443:127.0.0.1"
code=$(curl -ksS --connect-timeout 5 --max-time 12 -o /dev/null -w '%{http_code}' \
    --resolve "$RESOLVE" "$PUBLIC/healthz")
test "$code" = 200 || { echo "PUBLIC_8443_EXISTING_HEALTH=$code STOP"; exit 6; }
echo "PUBLIC_8443_BEFORE=200"

mkdir -m 700 "$WORK"
cp -p "$BASE" "$WORK/compose.original.yaml"
printf '%s\n' "$ORIGINAL" > "$WORK/original-image-id.txt"
rollback_tag="japanese-api:pre-plamo-rollback-$(basename "$WORK")"
sudo "$DOCKER" tag "$ORIGINAL" "$rollback_tag"
printf '%s\n' "services:" "  japanese-api:" "    image: $CANDIDATE" \
    "    volumes:" "      - $SOCKDIR:/run/plamo-gateway:ro" \
    > "$WORK/plamo.override.yaml"
printf '%s\n' "services:" "  japanese-api:" "    image: $rollback_tag" \
    > "$WORK/rollback.override.yaml"

cat > "$WORK/rollback.sh" <<EOS
#!/bin/sh
set -eu
sudo "$DOCKER" compose -p "$PROJECT" -f "$BASE" -f "$WORK/rollback.override.yaml" up -d --no-deps --no-build japanese-api
echo "ROLLBACK_TO_PREPLAMO_IMAGE=REQUESTED"
EOS
chmod 700 "$WORK/rollback.sh"

# Verify the composed candidate config points to the expected NEW image and
# *adds* a socket mount without removing existing audio/data bind mounts.
sudo "$DOCKER" compose -p "$PROJECT" -f "$BASE" -f "$WORK/plamo.override.yaml" \
    config --format json | python3 - "$CANDIDATE" "$SOCKDIR" <<'PY'
PY
# The line above uses stdin for two streams; intentionally replaced below.
