#!/bin/sh
# Step 9AL: translator-only cutover failure diagnosis. No production changes.
# This script never runs compose up/down/build/restart, never writes live DB,
# never tests wordlist/conjugation APIs, and never modifies the network.
set -eu
umask 077
DOCKER=/usr/local/bin/docker
ROOT=/volume2/docker/japanese-api
BACKUP="$HOME/japanese-api-rollbacks/preplamo-20261112_130956"
FAILED="$HOME/plamo-translation-deploy-20261112_200806"
CANDIDATE="japanese-api:plamo-8443-20261112_141623"
PROBE="$HOME/plamo-gateway-staging/isolated_uvicorn_translator_probe.py"
SOCKET_DIR="$HOME/plamo-gateway-run"
PUBLIC="https://kanu-rustdesk.synology.me:8443"
RESOLVE="kanu-rustdesk.synology.me:8443:127.0.0.1"

echo "=== STEP 9AL: TRANSLATOR 8443 FAILURE READ-ONLY DIAG ==="
test -x "$DOCKER"
test -f "$ROOT/compose.yaml"
test -f "$BACKUP/image-id.txt"
test -f "$BACKUP/api-source.tar.gz"
test -f "$FAILED/plamo.override.yaml"
test -f "$FAILED/rollback.override.yaml"
test -f "$PROBE"
test ! -L "$PROBE"
test -S "$SOCKET_DIR/gateway.sock"

original=$(cat "$BACKUP/image-id.txt")
expected=$(tar -xOzf "$BACKUP/api-source.tar.gz" app/main.py | sha256sum | awk '{print $1}')
actual=$(sha256sum "$ROOT/app/main.py" | awk '{print $1}')
test "$expected" = "$actual" || {
    echo "PRODUCTION_MAIN_CHANGED=STOP"; exit 4;
}
echo "PRODUCTION_SOURCE_MATCH=PASS"

sudo -v
current=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
if [ "$current" != "$original" ]; then
    echo "ROLLBACK_IMAGE_MISMATCH=STOP"; exit 5
fi
running=$(sudo "$DOCKER" inspect --format '{{.State.Running}}' japanese-api)
if [ "$running" != "true" ]; then
    echo "PRODUCTION_CONTAINER_NOT_RUNNING=STOP"; exit 5
fi
echo "ROLLBACK_ORIGINAL_IMAGE=PASS"
echo "PRODUCTION_CONTAINER_RUNNING=PASS"

# Check both internal loopback upstream and existing 8443 reverse proxy.
direct=$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:8015/healthz || true)
public=$(curl -ksS --max-time 12 -o /dev/null -w '%{http_code}' \
    --resolve "$RESOLVE" "$PUBLIC/healthz" || true)
echo "PRODUCTION_UPSTREAM_HEALTH_HTTP=$direct"
echo "PUBLIC_8443_ROLLBACK_HEALTH_HTTP=$public"
if [ "$direct" != 200 ] || [ "$public" != 200 ]; then
    echo "ROLLBACK_HEALTH_UNCONFIRMED=STOP_NO_FURTHER_TEST"
    exit 6
fi
echo "ROLLBACK_HEALTH=PASS"

sudo "$DOCKER" image inspect "$CANDIDATE" >/dev/null
project=$(sudo "$DOCKER" inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' japanese-api)
case "$project" in ''|*[!a-zA-Z0-9_-]*) echo "COMPOSE_PROJECT_INVALID=STOP"; exit 7 ;; esac

# Show only mount destinations/transport facts; never print environment,
# Compose content or Supabase credentials.
sudo "$DOCKER" compose -p "$project" -f "$ROOT/compose.yaml" \
    -f "$FAILED/plamo.override.yaml" config --format json | \
    python3 -c '
import json,sys
cfg=json.load(sys.stdin)
svc=cfg["services"]["japanese-api"]
vol=svc.get("volumes",[])
targets=set()
for v in vol:
    if isinstance(v,dict):
        targets.add(v.get("target"))
assert {"/srv/data","/srv/audio","/run/plamo-gateway"} <= targets
ports=svc.get("ports",[])
match=any(str(x.get("published"))=="8015" and str(x.get("target"))=="8000" for x in ports if isinstance(x,dict))
print("CANDIDATE_COMPOSE_DATA_AUDIO_SOCKET_MOUNTS=PASS")
print("CANDIDATE_COMPOSE_LOCAL_8015_TO_8000=%s" % ("PASS" if match else "NOT_CONFIRMED"))
print("CANDIDATE_COMPOSE_NETWORK_MODE=%s" % str(svc.get("network_mode") or "default"))
print("CANDIDATE_COMPOSE_COMMAND_PRESENT=%s" % bool(svc.get("command")))
'

# The real incident occurred in production Compose, not in the ASGI smoke.
# Test actual Uvicorn startup (not just import) in a disposable networkless
# container using EMPTY TMPFS. Never mount live Japanese SQLite or auth env.
echo "CANDIDATE_DISPOSABLE_UVICORN_TEST=START"
sudo "$DOCKER" run --rm --network none --read-only \
    --security-opt no-new-privileges --cap-drop ALL --cap-add DAC_OVERRIDE \
    --user 0:0 --tmpfs /tmp:rw,nosuid,nodev,size=32m \
    --tmpfs /srv/data:rw,nosuid,nodev,size=128m,mode=1777 \
    -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/srv \
    -v "$SOCKET_DIR:/run/plamo-gateway:ro" \
    -v "$ROOT/audio:/srv/audio:ro" \
    -v "/volume2/docker/japanese-voice-production/voicevox:/srv/voicevox-production:ro" \
    -v "$PROBE:/isolated-uvicorn-probe.py:ro" \
    --entrypoint python "$CANDIDATE" /isolated-uvicorn-probe.py
echo "CANDIDATE_DISPOSABLE_UVICORN_TEST=PASS"

current_after=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
test "$current_after" = "$original" || {
    echo "PRODUCTION_IMAGE_CHANGED_DURING_DIAG=STOP"; exit 8;
}
echo "PRODUCTION_IMAGE_STILL_ORIGINAL=PASS"
echo "PRODUCTION_CONTAINER_RESTARTED_BY_DIAG=NO"
echo "PRODUCTION_SQLITE_OPENED_BY_DIAG=NO"
echo "NO_DEPLOY_ATTEMPTED=PASS"
echo "STEP_9AL=PASS"
