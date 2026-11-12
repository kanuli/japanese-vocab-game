#!/bin/sh
# STEP 9AH — Build and smoke-test isolated HTTPS 8443 PLaMo candidate.
# Only creates a private build directory and NEW candidate Docker image.
# Does not edit the live app, Compose, Gateway, router, or nginx; no restarts.
set -eu
umask 077

ROOT=/volume2/docker/japanese-api
STAGE="$HOME/plamo-gateway-staging"
SOCK="$HOME/plamo-gateway-run/gateway.sock"
BACKUP="$HOME/japanese-api-rollbacks/preplamo-20261112_130956/api-source.tar.gz"
DOCKER=/usr/local/bin/docker
STAMP=$(date +%Y%m%d_%H%M%S)
DEST="$HOME/japanese-api-candidates/plamo-8443-$STAMP"
TAG="japanese-api:plamo-8443-$STAMP"

echo "=== STEP 9AH-B: OFFLINE OVERLAY BUILD OF 8443 CANDIDATE ==="
test -f "$BACKUP"
test -f "$ROOT/app/main.py"
test -f "$ROOT/Dockerfile"
test -f "$ROOT/requirements.txt"
test -f "$ROOT/compose.yaml"
test -f "$STAGE/japanese_api_router.py"
test -S "$SOCK"
test -x "$DOCKER"

# Ensure live source matches the already verified rollback snapshot.
expected=$(tar -xOzf "$BACKUP" app/main.py | sha256sum | awk '{print $1}')
actual=$(sha256sum "$ROOT/app/main.py" | awk '{print $1}')
if [ "$actual" != "$expected" ]; then
    echo "LIVE_MAIN_CHANGED_SINCE_BACKUP=STOP"
    exit 2
fi
echo "BACKUP_SOURCE_MATCH=PASS"

# Do not perform a Docker build on a nearly full volume.
available_kb=$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')
case "$available_kb" in
    ''|*[!0-9]*) echo "FREE_SPACE_UNKNOWN=STOP"; exit 3 ;;
esac
if [ "$available_kb" -lt 1048576 ]; then
    echo "FREE_SPACE_BELOW_1G=STOP"
    exit 3
fi
echo "FREE_SPACE_GATE=PASS"

# Check socket is a real working NAS gateway (not stale filesystem entry).
python3 - "$SOCK" <<'PY'
import socket, sys
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(4)
try:
    sock.connect(sys.argv[1])
    sock.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    result = sock.recv(1024)
finally:
    sock.close()
if b"HTTP/1.0 200" not in result and b"HTTP/1.1 200" not in result:
    raise SystemExit("UDS_GATEWAY_HEALTH=FAIL")
print("UDS_GATEWAY_HEALTH=PASS")
PY

# Confirm original gateway is untouched and listening on NAS loopback.
python3 - <<'PY'
import http.client
conn = http.client.HTTPConnection("127.0.0.1", 18790, timeout=5)
conn.request("GET", "/healthz")
reply = conn.getresponse()
reply.read()
conn.close()
if reply.status != 200:
    raise SystemExit("ORIGINAL_GATEWAY=FAIL")
print("ORIGINAL_GATEWAY=200")
PY

mkdir -p "$DEST"
chmod 700 "$DEST"
cp -R "$ROOT/app" "$DEST/app"
cp "$ROOT/Dockerfile" "$ROOT/requirements.txt" "$DEST/"
cp "$ROOT/compose.yaml" "$DEST/compose-reference.yaml"
cp "$STAGE/japanese_api_router.py" "$DEST/app/plamo_translate_routes.py"

python3 - "$DEST/app/main.py" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text(encoding="utf-8")
old = 'allow_methods=["GET", "HEAD", "OPTIONS"]'
new = 'allow_methods=["GET", "HEAD", "OPTIONS", "POST"]'
if s.count(old) != 1:
    raise SystemExit("CORS_EXPECTED_CONFIGURATION_NOT_FOUND=STOP")
if 'plamo_translate_routes' in s:
    raise SystemExit("PLAMO_ROUTE_ALREADY_PRESENT=STOP")
if s.count('app.include_router(voicevox_production_router)') != 1:
    raise SystemExit("EXISTING_VOICEVOX_ROUTER_UNEXPECTED=STOP")
s = s.replace(old, new, 1)
s = s.rstrip() + ('\n\nfrom app.plamo_translate_routes import router as plamo_translate_router\n'
                  'app.include_router(plamo_translate_router)\n')
p.write_text(s, encoding="utf-8")
print("CANDIDATE_CORS_POST=PASS")
print("CANDIDATE_PLAMO_ROUTER=PASS")
PY
python3 -m py_compile "$DEST/app/main.py" "$DEST/app/plamo_translate_routes.py"
echo "CANDIDATE_SOURCE_SYNTAX=PASS"

# Test real current image access before changing anything.
image=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
case "$image" in sha256:*) ;; *) echo "LIVE_IMAGE_UNKNOWN=STOP"; exit 4;; esac
printf '%s\n' "$image" > "$DEST/production-image-id.txt"

# Build from the exact currently running API image, which ALREADY includes
# pinned FastAPI/Uvicorn dependencies. This avoids pip install entirely.
# IMPORTANT: The normal production Dockerfile has RUN pip install --no-cache-dir,
# which cannot execute with --network=none, even if an image previously built.
BASE_TAG="japanese-api:plamo-9ah-base-$STAMP"
sudo "$DOCKER" tag "$image" "$BASE_TAG"
mv "$DEST/Dockerfile" "$DEST/Dockerfile.production-reference"
printf 'FROM %s\nCOPY app /srv/app\n' "$BASE_TAG" > "$DEST/Dockerfile"
echo "CANDIDATE_DOCKERFILE=OFFLINE_OVERLAY"
echo "CANDIDATE_BASE_IMAGE=EXACT_PRODUCTION_IMAGE"
# The overlay Dockerfile has NO RUN, curl or pip instructions.
if grep -Eiq '^([[:space:]]*)(RUN|ADD)[[:space:]]' "$DEST/Dockerfile"; then
    echo "CANDIDATE_DOCKERFILE_UNEXPECTED_ACTION=STOP"
    exit 5
fi
sudo "$DOCKER" build --pull=false --network=none -t "$TAG" "$DEST"
echo "CANDIDATE_DOCKER_BUILD=PASS"

cat > "$DEST/smoke.py" <<'PY'
import asyncio
import importlib
import json
import socket

app = importlib.import_module("app.main").app
paths = {r.path for r in app.routes}
assert "/api/v1/translate/plamo" in paths
assert "/healthz" in paths
print("REAL_APP_IMPORT_AND_ROUTES=PASS")

async def request(method, path, body=None, headers=None):
    body = body or b""
    headers = dict(headers or {})
    if method == "POST":
        headers["content-type"] = "application/json"
        headers["content-length"] = str(len(body))
    scope = {
        "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1", "method": method, "scheme": "https",
        "path": path, "raw_path": path.encode("ascii"), "root_path": "",
        "query_string": b"",
        "headers": [(k.lower().encode("ascii"), v.encode("latin1"))
                    for k, v in headers.items()],
        "client": ("192.0.2.15", 12345), "server": ("testserver", 443),
    }
    emitted = []
    received = False
    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}
    async def send(message):
        emitted.append(message)
    await app(scope, receive, send)
    start = [e for e in emitted if e["type"] == "http.response.start"]
    if len(start) != 1:
        raise AssertionError("Unexpected ASGI response framing")
    h = {k.decode("latin1"): v.decode("latin1") for k, v in start[0]["headers"]}
    return start[0]["status"], h

ORIGIN = "https://kanuli.github.io"
PATH = "/api/v1/translate/plamo"
p, h = asyncio.run(request("OPTIONS", PATH, headers={
    "origin": ORIGIN, "access-control-request-method": "POST",
    "access-control-request-headers": "authorization,content-type",
}))
assert p == 200, ("CORS_PREFLIGHT", p)
assert h.get("access-control-allow-origin") == ORIGIN
assert "POST" in h.get("access-control-allow-methods", "")
print("REAL_APP_CORS_PREFLIGHT_POST=PASS")

payload = json.dumps({"source_lang": "ja", "target_lang": "en", "text": "こんにちは"}).encode()
p, h = asyncio.run(request("POST", PATH, body=payload, headers={"origin": ORIGIN}))
assert p == 401, ("MISSING_AUTH", p)
print("REAL_APP_UNAUTHENTICATED_REJECTED=PASS")

p, h = asyncio.run(request("GET", "/healthz"))
assert p == 200, ("HEALTHZ", p)
print("REAL_APP_HEALTHZ=PASS")

# Real mounted UDS to independent NAS-host shadow Gateway; NO auth request.
u = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
u.settimeout(5)
try:
    u.connect("/run/plamo-gateway/gateway.sock")
    u.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
    response = u.recv(1024)
finally:
    u.close()
assert b"HTTP/1.0 200" in response or b"HTTP/1.1 200" in response
print("CANDIDATE_DOCKER_TO_REAL_SHADOW_GATEWAY=PASS")
print("CANDIDATE_SMOKE_TEST=PASS")
PY

# Build context uses umask 077 (private). The bind-mounted smoke.py is
# NOT sensitive; explicitly allow the image's container user to read it.
# Keep the candidate directory private and do not relax any secret/socket modes.
chmod 644 "$DEST/smoke.py"
echo "CANDIDATE_SMOKE_FILE_MODE=0644"

echo "SMOKE_DB=ISOLATED_TMPFS_NO_PRODUCTION_DB_MOUNT"
# Private 0700/0600 UDS is NAS-user-owned; image app code is root-owned
# and inaccessible to NAS UID. For THIS disposable no-network smoke only,
# root plus *only* CAP_DAC_OVERRIDE reads both; other capabilities dropped.
# Production deployment must separately validate a least-privilege identity.
python3 - "$HOME/plamo-gateway-run" <<'PY'
import os
import stat
import sys
directory = sys.argv[1]
sock = os.path.join(directory, "gateway.sock")
d = os.stat(directory, follow_symlinks=False)
s = os.stat(sock, follow_symlinks=False)
if not stat.S_ISDIR(d.st_mode) or not stat.S_ISSOCK(s.st_mode):
    raise SystemExit("SOCKET_TYPE_INVALID=STOP")
if d.st_uid != os.getuid() or s.st_uid != os.getuid():
    raise SystemExit("SOCKET_OWNER_MISMATCH=STOP")
if (d.st_mode & 0o777) != 0o700 or (s.st_mode & 0o777) != 0o600:
    raise SystemExit("SOCKET_PERMISSIONS_UNEXPECTED=STOP")
print("SOCKET_MODE_0700_0600=PASS")
print("SOCKET_OWNERSHIP_VERIFIED=PASS")
PY
sudo "$DOCKER" run --rm --network none --read-only \
    --security-opt no-new-privileges --cap-drop ALL --cap-add DAC_OVERRIDE \
    --user 0:0 \
    --tmpfs /tmp:rw,nosuid,nodev,size=32m \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PYTHONPATH=/srv \
    -v "$HOME/plamo-gateway-run:/run/plamo-gateway:ro" \
    --tmpfs /srv/data:rw,nosuid,nodev,size=128m,mode=1777 \
    -v "$ROOT/audio:/srv/audio:ro" \
    -v "/volume2/docker/japanese-voice-production/voicevox:/srv/voicevox-production:ro" \
    -v "$DEST/smoke.py:/smoke.py:ro" \
    --entrypoint python "$TAG" /smoke.py

# Verify original API files and image ID still exactly unchanged.
after=$(sha256sum "$ROOT/app/main.py" | awk '{print $1}')
test "$after" = "$actual"
current=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
test "$current" = "$image"
echo "PRODUCTION_SOURCE_UNCHANGED=PASS"
echo "PRODUCTION_IMAGE_UNCHANGED=PASS"
echo "PRODUCTION_CONTAINER_RESTARTED=NO"
echo "ORIGINAL_GATEWAY_RESTARTED=NO"
echo "CANDIDATE_IMAGE_TAG=$TAG"
echo "LOCAL_BASE_TAG=$BASE_TAG"
echo "CANDIDATE_DIRECTORY=$DEST"
echo "STEP_9AH_B=PASS"
