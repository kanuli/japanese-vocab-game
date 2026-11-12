#!/bin/sh
# STEP 9AH-C: resume ONLY the prebuilt candidate's failed smoke test.
# DO NOT rebuild, restart, modify live API, Gateway or Compose.
set -eu
umask 077
DOCKER=/usr/local/bin/docker
ROOT=/volume2/docker/japanese-api
DEST="$HOME/japanese-api-candidates/plamo-8443-20261112_141623"
TAG="japanese-api:plamo-8443-20261112_141623"
BACKUP="$HOME/japanese-api-rollbacks/preplamo-20261112_130956/api-source.tar.gz"
SOCKET_DIR="$HOME/plamo-gateway-run"
SMOKE="$DEST/smoke.py"

echo "=== STEP 9AH-C: REUSE EXISTING CANDIDATE ==="
test -f "$BACKUP" && test -f "$ROOT/app/main.py"
test -d "$DEST" && test ! -L "$DEST"
test -f "$SMOKE" && test ! -L "$SMOKE"
test -S "$SOCKET_DIR/gateway.sock"

expected=$(tar -xOzf "$BACKUP" app/main.py | sha256sum | awk '{print $1}')
actual=$(sha256sum "$ROOT/app/main.py" | awk '{print $1}')
if [ "$expected" != "$actual" ]; then
    echo "PRODUCTION_SOURCE_CHANGED=STOP"
    exit 2
fi
echo "BACKUP_SOURCE_MATCH=PASS"

# The 077 umask intentionally created a 0600 script. The script is not
# confidential; allow readonly container user to open this ONE file.
# Do NOT chmod the source tree, gateway config, socket, or parent directory.
chmod 644 "$SMOKE"
echo "SMOKE_FILE_READABLE=PASS"

# Verify the exact previously built local tag and original production ID.
image=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
test "$image" = "$(cat "$DEST/production-image-id.txt")"
sudo "$DOCKER" image inspect "$TAG" >/dev/null
echo "EXISTING_CANDIDATE_IMAGE=PASS"
echo "PRODUCTION_IMAGE_UNCHANGED=PASS"

# Run candidate ASGI smoke and real shadow UDS GET, no outbound networking.
sudo "$DOCKER" run --rm \
    --network none --read-only \
    --security-opt no-new-privileges --cap-drop ALL \
    --tmpfs /tmp:rw,nosuid,nodev,size=32m \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -v "$SOCKET_DIR:/run/plamo-gateway:ro" \
    -v "$ROOT/data:/srv/data:ro" \
    -v "$ROOT/audio:/srv/audio:ro" \
    -v "/volume2/docker/japanese-voice-production/voicevox:/srv/voicevox-production:ro" \
    -v "$SMOKE:/smoke.py:ro" \
    --entrypoint python "$TAG" /smoke.py

echo "PRODUCTION_SOURCE_UNCHANGED=PASS"
echo "PRODUCTION_CONTAINER_RESTARTED=NO"
echo "ORIGINAL_GATEWAY_RESTARTED=NO"
echo "CANDIDATE_IMAGE_TAG=$TAG"
echo "STEP_9AH_C=PASS"
