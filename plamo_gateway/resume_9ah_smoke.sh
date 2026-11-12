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

echo "=== STEP 9AH-G: RESUME ISOLATED SMOKE WITH DAC_OVERRIDE ==="
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

# Candidate API init_db() writes ONLY into an empty, disposable tmpfs.
# No production DB is mounted in the container. This validates startup and
# route mechanics; data-backed regressions will use a separate safe snapshot.
# Run candidate ASGI smoke and real shadow UDS GET, no outbound networking.
sudo "$DOCKER" run --rm \
    --network none --read-only \
    --security-opt no-new-privileges --cap-drop ALL --cap-add DAC_OVERRIDE \
    --user 0:0 \
    --tmpfs /tmp:rw,nosuid,nodev,size=32m \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PYTHONPATH=/srv \
    -v "$SOCKET_DIR:/run/plamo-gateway:ro" \
    --tmpfs /srv/data:rw,nosuid,nodev,size=128m,mode=1777 \
    -v "$ROOT/audio:/srv/audio:ro" \
    -v "/volume2/docker/japanese-voice-production/voicevox:/srv/voicevox-production:ro" \
    -v "$SMOKE:/smoke.py:ro" \
    --entrypoint python "$TAG" /smoke.py

test "$(sha256sum "$ROOT/app/main.py" | awk '{print $1}')" = "$expected"
test "$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)" = "$image"
echo "PRODUCTION_SOURCE_UNCHANGED=PASS"
echo "PRODUCTION_IMAGE_UNCHANGED_AFTER=PASS"
echo "PRODUCTION_CONTAINER_RESTARTED=NO"
echo "ORIGINAL_GATEWAY_RESTARTED=NO"
echo "CANDIDATE_IMAGE_TAG=$TAG"
echo "STEP_9AH_G=PASS"
