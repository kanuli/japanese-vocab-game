#!/bin/sh
# Step 9AG: Start NEW UDS-only PLaMo shadow gateway alongside existing
# localhost:18790 Gateway; prove temporary Docker -> real NAS UDS connectivity.
# No source, Compose, router, main, Nginx, firewall, or existing process changes.
set -eu
umask 077

STAGE="$HOME/plamo-gateway-staging"
CONFIG="$HOME/.config/plamo-gateway/config.env"
SOCKET_DIR="$HOME/plamo-gateway-run"
SOCK="$SOCKET_DIR/gateway.sock"
PIDFILE="$SOCKET_DIR/shadow.pid"
LOG="$SOCKET_DIR/shadow.log"
DOCKER="/usr/local/bin/docker"
started=0
pid=""

rollback_if_error() {
    code=$?
    if [ "$code" -ne 0 ] && [ "$started" -eq 1 ]; then
        echo "ROLLBACK_SHADOW_GATEWAY=START"
        kill "$pid" 2>/dev/null || true
        sleep 1
        if ! kill -0 "$pid" 2>/dev/null; then
            rm -f "$PIDFILE" "$SOCK"
            echo "ROLLBACK_SHADOW_GATEWAY=PASS"
        else
            echo "ROLLBACK_SHADOW_GATEWAY=CHECK_PROCESS"
        fi
    fi
}
trap rollback_if_error EXIT

echo "=== STEP 9AG: NONDISRUPTIVE UDS SHADOW GATEWAY ==="
test -f "$STAGE/gateway_uds_candidate.py"
test -f "$STAGE/test_gateway_unix.py"
test -f "$STAGE/japanese_api_router.py"
test -f "$CONFIG" && test -r "$CONFIG" && test ! -L "$CONFIG"
test -x "$DOCKER"
python3 -m py_compile "$STAGE/gateway_uds_candidate.py"
echo "CANDIDATE_SYNTAX=PASS"

python3 - <<'PY'
import http.client
c = http.client.HTTPConnection("127.0.0.1", 18790, timeout=4)
c.request("GET", "/healthz")
r = c.getresponse()
r.read()
c.close()
if r.status != 200:
    raise SystemExit("ORIGINAL_GATEWAY_HEALTH=FAIL")
print("ORIGINAL_GATEWAY_HEALTH=200")
PY

# Request sudo before launching anything; see a native NAS password prompt.
image=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
case "$image" in
    sha256:*) echo "PRODUCTION_IMAGE_IDENTIFIED=PASS" ;;
    *) echo "PRODUCTION_IMAGE_IDENTIFIED=FAIL"; exit 2 ;;
esac

mkdir -p "$SOCKET_DIR"
chmod 700 "$SOCKET_DIR"
if [ -e "$SOCK" ] || [ -L "$SOCK" ] || [ -e "$PIDFILE" ]; then
    echo "SHADOW_STATE_ALREADY_PRESENT=STOP_FOR_REVIEW"
    exit 3
fi

# Source the already-existing private configuration without printing values.
# No secrets go through PowerShell arguments, GitHub, or chat.
(
    set -a
    . "$CONFIG"
    set +a
    : "${PLAMO_SUPABASE_URL:?}"
    : "${PLAMO_SUPABASE_PUBLISHABLE_KEY:?}"
    : "${PLAMO_ALLOWED_USER_IDS:?}"
    export PLAMO_UNIX_ONLY=1
    export PLAMO_UNIX_SOCKET="$SOCK"
    exec python3 "$STAGE/gateway_uds_candidate.py"
) > "$LOG" 2>&1 < /dev/null &
pid=$!
started=1
printf '%s\n' "$pid" > "$PIDFILE"

ready=0
for attempt in 1 2 3 4 5 6; do
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    if [ -S "$SOCK" ]; then ready=1; break; fi
    sleep 1
done
if [ "$ready" -ne 1 ]; then
    echo "SHADOW_SOCKET_READY=FAIL"
    exit 4
fi
echo "SHADOW_SOCKET_READY=PASS"

python3 - "$SOCK" <<'PY'
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(5)
s.connect(sys.argv[1])
s.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
data = s.recv(1024)
s.close()
if b"HTTP/1.0 200" not in data and b"HTTP/1.1 200" not in data:
    raise SystemExit("NAS_SHADOW_UDS_HEALTH=FAIL")
print("NAS_SHADOW_UDS_HEALTH=PASS")
PY

# Production image, but a NEW disposable read-only test container with no
# network and only the restricted socket-directory mount.
sudo "$DOCKER" run --rm --network none --read-only \
    --security-opt no-new-privileges \
    --tmpfs /tmp:rw,nosuid,nodev,size=16m \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$SOCKET_DIR:/run/plamo-gateway:ro" \
    -v "$STAGE:/staging:ro" \
    -w /staging --entrypoint python "$image" -c '
import socket
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.settimeout(5)
s.connect("/run/plamo-gateway/gateway.sock")
s.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
data = s.recv(1024)
s.close()
assert b"HTTP/1.0 200" in data or b"HTTP/1.1 200" in data
print("DOCKER_TO_REAL_GATEWAY_UDS=PASS")
'

python3 - <<'PY'
import http.client
c = http.client.HTTPConnection("127.0.0.1", 18790, timeout=4)
c.request("GET", "/healthz")
r = c.getresponse()
r.read()
c.close()
if r.status != 200:
    raise SystemExit("ORIGINAL_GATEWAY_STILL_HEALTHY=FAIL")
print("ORIGINAL_GATEWAY_STILL_HEALTHY=PASS")
PY

echo "PRODUCTION_SOURCE_MODIFIED=NO"
echo "PRODUCTION_CONTAINER_RESTARTED=NO"
echo "EXISTING_GATEWAY_RESTARTED=NO"
echo "SHADOW_GATEWAY_STARTED=YES"
echo "STEP_9AG=PASS"
