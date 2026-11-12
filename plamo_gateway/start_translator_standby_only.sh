#!/bin/sh
# 9AS: stage ONLY the PLaMo translator API as an independent NAS loopback service.
# Does not modify production Japanese API, Compose, nginx, GitHub Pages or DB.
# This is a STANDBY; live 8443 is UNCHANGED until dedicated path routing is ready.
set -eu
umask 077
DOCKER=/usr/local/bin/docker
ROOT=/volume2/docker/japanese-api
BACKUP="$HOME/japanese-api-rollbacks/preplamo-20261112_130956"
IMG="japanese-api:plamo-8443-20261112_141623"
SOCKDIR="$HOME/plamo-gateway-run"
NAME="plamo-translator-standby"
HOSTPORT=18015
PUBLIC="https://kanu-rustdesk.synology.me:8443/healthz"
RESOLVE="kanu-rustdesk.synology.me:8443:127.0.0.1"
CREATED=0
READY=0

cleanup() {
    code=$?
    trap - EXIT HUP INT TERM
    if [ "$CREATED" -eq 1 ] && [ "$READY" -ne 1 ]; then
        sudo -n "$DOCKER" rm -f "$NAME" >/dev/null 2>&1 || true
        echo "FAILED_STANDBY_REMOVAL=ATTEMPTED"
    fi
    exit "$code"
}
trap cleanup EXIT HUP INT TERM

echo "=== STEP 9AS: PLAMO TRANSLATOR STANDBY ==="
test -f "$BACKUP/image-id.txt"
test -f "$BACKUP/api-source.tar.gz"
test -f "$ROOT/app/main.py"
test -d "$ROOT/audio"
test -d /volume2/docker/japanese-voice-production/voicevox
test -S "$SOCKDIR/gateway.sock"
test ! -L "$SOCKDIR"
test -x "$DOCKER"
old=$(tar -xOzf "$BACKUP/api-source.tar.gz" app/main.py | sha256sum | awk '{print $1}')
now=$(sha256sum "$ROOT/app/main.py" | awk '{print $1}')
test "$old" = "$now" || { echo "LIVE_SOURCE_CHANGED=STOP"; exit 5; }

sudo -v
oldimage=$(cat "$BACKUP/image-id.txt")
liveimage=$(sudo -n "$DOCKER" inspect --format '{{.Image}}' japanese-api)
test "$oldimage" = "$liveimage" || { echo "ORIGINAL_IMAGE_NOT_RUNNING=STOP"; exit 5; }
sudo -n "$DOCKER" image inspect "$IMG" >/dev/null
before=$(curl -ksS --connect-timeout 4 --max-time 12 --resolve "$RESOLVE" -o /dev/null -w '%{http_code}' "$PUBLIC")
test "$before" = 200 || { echo "LIVE_8443_BEFORE=$before STOP"; exit 6; }
echo "LIVE_8443_BEFORE=200"

# Never overwrite or stop a container with this name without explicit review.
if sudo -n "$DOCKER" container inspect "$NAME" >/dev/null 2>&1; then
    echo "STANDBY_NAME_EXISTS=STOP_MANUAL_REVIEW"
    exit 7
fi

# Only host loopback, not WAN or NAS LAN. No production SQLite mount.
# Data is a disposable tmpfs as validated by earlier default-CMD probes.
id=$(sudo -n "$DOCKER" create \
    --name "$NAME" --restart no \
    --network bridge -p "127.0.0.1:$HOSTPORT:8000" \
    --read-only --security-opt no-new-privileges \
    --cap-drop ALL --cap-add DAC_OVERRIDE --user 0:0 \
    --tmpfs /tmp:rw,nosuid,nodev,size=32m \
    --tmpfs /srv/data:rw,nosuid,nodev,size=128m,mode=1777 \
    -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/srv \
    -v "$SOCKDIR:/run/plamo-gateway:ro" \
    -v "$ROOT/audio:/srv/audio:ro" \
    -v "/volume2/docker/japanese-voice-production/voicevox:/srv/voicevox-production:ro" \
    "$IMG")
case "$id" in
    *[!0123456789abcdef]*|'') echo "CONTAINER_ID_INVALID=STOP"; exit 8 ;;
esac
CREATED=1
sudo -n "$DOCKER" start "$NAME" >/dev/null
echo "STANDBY_DOCKER_STARTED=PASS"

status=000
n=0
while [ "$n" -lt 40 ]; do
    n=$((n + 1))
    status=$(curl -sS --connect-timeout 2 --max-time 3 \
        -o /dev/null -w '%{http_code}' "http://127.0.0.1:$HOSTPORT/healthz" 2>/dev/null || true)
    if [ "$status" = 200 ]; then break; fi
    sleep 1
done
test "$status" = 200 || { echo "STANDBY_HEALTH_HTTP=$status FAIL"; exit 9; }
echo "STANDBY_LOOPBACK_HEALTH=200"

# Actual image identity and published host loopback binding.
actual=$(sudo -n "$DOCKER" inspect --format '{{.Config.Image}}' "$NAME")
test "$actual" = "$IMG"
port=$(sudo -n "$DOCKER" port "$NAME" 8000/tcp)
test "$port" = "127.0.0.1:$HOSTPORT" || {
    echo "STANDBY_UNEXPECTED_PORT_BIND=STOP"; exit 10;
}
echo "STANDBY_PORT_LOOPBACK_ONLY=PASS"

# Requests without a Supabase bearer must be rejected.
post=$(curl -sS --connect-timeout 3 --max-time 8 \
    -o /dev/null -w '%{http_code}' \
    -H "Origin: https://kanuli.github.io" \
    -H "Content-Type: application/json" \
    --data '{"source_lang":"ja","target_lang":"en","text":"こんにちは"}' \
    "http://127.0.0.1:$HOSTPORT/api/v1/translate/plamo")
test "$post" = 401 || { echo "STANDBY_UNAUTH_HTTP=$post FAIL"; exit 11; }
echo "STANDBY_UNAUTH_401=PASS"

# Check browser preflight. Output headers retained only in private temp file.
headers=$(mktemp)
trap 'rm -f "$headers"; cleanup' EXIT HUP INT TERM
cors=$(curl -sS --connect-timeout 3 --max-time 8 -D "$headers" \
    -o /dev/null -w '%{http_code}' -X OPTIONS \
    -H "Origin: https://kanuli.github.io" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: authorization,content-type" \
    "http://127.0.0.1:$HOSTPORT/api/v1/translate/plamo")
case "$cors" in 200|204) ;; *) echo "STANDBY_CORS_HTTP=$cors FAIL"; exit 12 ;; esac
grep -iq '^access-control-allow-origin: https://kanuli.github.io' "$headers"
grep -iq '^access-control-allow-methods:.*POST' "$headers"
rm -f "$headers"
trap cleanup EXIT HUP INT TERM
echo "STANDBY_CORS=PASS"

bad=$(curl -sS --connect-timeout 3 --max-time 8 \
    -o /dev/null -w '%{http_code}' \
    -H "Origin: https://invalid-origin.example" \
    -H "Content-Type: application/json" \
    --data '{"source_lang":"ja","target_lang":"en","text":"こんにちは"}' \
    "http://127.0.0.1:$HOSTPORT/api/v1/translate/plamo")
test "$bad" = 403 || { echo "STANDBY_BAD_ORIGIN_HTTP=$bad FAIL"; exit 13; }
echo "STANDBY_BAD_ORIGIN_403=PASS"

after=$(curl -ksS --connect-timeout 4 --max-time 12 --resolve "$RESOLVE" -o /dev/null -w '%{http_code}' "$PUBLIC")
test "$after" = 200 || { echo "LIVE_8443_AFTER=$after FAIL"; exit 14; }
test "$(sudo -n "$DOCKER" inspect --format '{{.Image}}' japanese-api)" = "$oldimage"
echo "LIVE_8443_AFTER=200"
echo "PRODUCTION_IMAGE_UNCHANGED=PASS"
echo "PRODUCTION_SQLITE_MOUNTED=NO"
echo "PRODUCTION_API_RESTARTED=NO"
echo "NGINX_CONFIGURATION_CHANGED=NO"
echo "WAN_LISTENER_CREATED=NO"
echo "SIDECAR_KEEP_RUNNING=YES"
echo "PUBLIC_PLAMO_ROUTE_ACTIVATED=NO"
READY=1
echo "STEP_9AS=PASS"
