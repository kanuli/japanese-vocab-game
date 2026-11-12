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
case "$PROJECT" in ''|*[!a-zA-Z0-9_-]*) echo "UNKNOWN_COMPOSE_PROJECT=STOP"; exit 5 ;; esac
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

# Verify the composed candidate config, preserving existing data/audio mounts.
# JSON config may contain environment values: parse in a pipeline without saving
# it or printing it to console.
sudo "$DOCKER" compose -p "$PROJECT" -f "$BASE" -f "$WORK/plamo.override.yaml" \
    config --format json | python3 -c '
import json,os,sys
try:
    cfg=json.load(sys.stdin)
    svc=cfg["services"]["japanese-api"]
    assert svc.get("image")==sys.argv[1]
    mounts=svc.get("volumes",[])
    targets={v.get("target") if isinstance(v,dict) else v.split(":")[1] for v in mounts}
    assert {"/srv/data","/srv/audio","/run/plamo-gateway"}<=targets
    uds=[v for v in mounts if isinstance(v,dict) and v.get("target")=="/run/plamo-gateway"]
    assert len(uds)==1
    assert os.path.realpath(uds[0]["source"])==os.path.realpath(sys.argv[2])
    assert bool(uds[0].get("read_only"))
except Exception:
    raise SystemExit("CANDIDATE_COMPOSE_CONFIG=FAIL")
print("CANDIDATE_COMPOSE_CONFIG=PASS")
' "$CANDIDATE" "$SOCKDIR"

echo "ROLLBACK_SCRIPT=$WORK/rollback.sh"
echo "TRANSLATOR_8443_DEPLOY=START"
DEployed=1
sudo "$DOCKER" compose -p "$PROJECT" -f "$BASE" -f "$WORK/plamo.override.yaml" \
    up -d --no-deps --no-build japanese-api

# Only check translation route and generic health (not wordlist/conjugation).
health=000
for attempt in 1 2 3 4 5 6 7 8 9 10 11 12; do
    health=$(curl -ksS --connect-timeout 3 --max-time 5 \
        --resolve "$RESOLVE" -o /dev/null -w '%{http_code}' \
        "$PUBLIC/healthz" || true)
    if [ "$health" = 200 ]; then break; fi
    sleep 2
done
test "$health" = 200 || {
    echo "PUBLIC_8443_HEALTH_AFTER=$health STOP_AND_ROLLBACK"
    exit 7
}
echo "PUBLIC_8443_HEALTH_AFTER=200"

# Public no-token test must reach FastAPI and be rejected, never call model.
unauth=$(curl -ksS --connect-timeout 5 --max-time 12 \
    --resolve "$RESOLVE" -o /dev/null -w '%{http_code}' \
    -H "Origin: https://kanuli.github.io" \
    -H "Content-Type: application/json" \
    --data '{"source_lang":"ja","target_lang":"en","text":"こんにちは"}' \
    "$PUBLIC/api/v1/translate/plamo")
if [ "$unauth" != 401 ]; then
    echo "PUBLIC_8443_PLAMO_NO_TOKEN_HTTP=$unauth STOP_AND_ROLLBACK"
    exit 8
fi
echo "PUBLIC_8443_PLAMO_NO_TOKEN_401=PASS"

# Browser preflight: no real credentials or user translation are sent.
preflight=$(curl -ksS --connect-timeout 5 --max-time 12 \
    --resolve "$RESOLVE" -D "$WORK/preflight.headers" \
    -o /dev/null -w '%{http_code}' -X OPTIONS \
    -H "Origin: https://kanuli.github.io" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: authorization,content-type" \
    "$PUBLIC/api/v1/translate/plamo")
case "$preflight" in 200|204) ;; *)
    echo "PUBLIC_8443_PLAMO_PREFLIGHT_HTTP=$preflight STOP_AND_ROLLBACK"
    exit 9 ;;
esac
grep -iq "^access-control-allow-origin: https://kanuli.github.io" "$WORK/preflight.headers" || {
    echo "PUBLIC_PREFLIGHT_ORIGIN_MISSING=STOP_AND_ROLLBACK"; exit 9;
}
grep -iq "^access-control-allow-methods:.*POST" "$WORK/preflight.headers" || {
    echo "PUBLIC_PREFLIGHT_POST_MISSING=STOP_AND_ROLLBACK"; exit 9;
}
rm -f "$WORK/preflight.headers"
echo "PUBLIC_8443_PLAMO_POST_PREFLIGHT=PASS"

# Reject foreign origin, even with no token.
bad_origin=$(curl -ksS --connect-timeout 5 --max-time 12 \
    --resolve "$RESOLVE" -o /dev/null -w '%{http_code}' \
    -H "Origin: https://not-your-website.example" \
    -H "Content-Type: application/json" \
    --data '{"source_lang":"ja","target_lang":"en","text":"こんにちは"}' \
    "$PUBLIC/api/v1/translate/plamo")
if [ "$bad_origin" != 403 ]; then
    echo "PUBLIC_8443_BAD_ORIGIN_HTTP=$bad_origin STOP_AND_ROLLBACK"
    exit 9
fi
echo "PUBLIC_8443_BAD_ORIGIN_403=PASS"

# Final original TCP Gateway check, no original process change.
python3 - <<'PY'
import http.client
c=http.client.HTTPConnection("127.0.0.1",18790,timeout=5)
c.request("GET","/healthz")
r=c.getresponse()
r.read()
c.close()
if r.status!=200: raise SystemExit("ORIGINAL_GATEWAY_HEALTH=FAIL")
print("ORIGINAL_GATEWAY_HEALTH=200")
PY

# Only after all tests pass, leave the single API container on candidate.
COMMITTED=1
printf '%s\n' "deployed" > "$WORK/deployed.marker"
echo "PRODUCTION_PAGES_SOURCE_CHANGED=NO"
echo "PRODUCTION_SQLITE_MODIFIED_BY_SCRIPT=NO"
echo "NEW_WAN_PORTS=NO"
echo "SHARED_API_CONTAINER_RECREATED=YES"
echo "TRANSLATOR_NAS_API_8443=READY"
echo "PUBLIC_FRONTEND_GITHUB_MAIN_UNCHANGED=YES"
echo "DEPLOY_TRANSLATOR_8443=PASS"
