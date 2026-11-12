#!/bin/sh
# 9AJ-D: Diagnose missing stderr from ORIGINAL image probe, no DB snapshots.
# Disposable container only: no live DB bind mounts, no network, no changes.
set -eu
umask 077

DOCKER=/usr/local/bin/docker
ROOT=/volume2/docker/japanese-api
STAGE="$HOME/plamo-gateway-staging"
BACKUP="$HOME/japanese-api-rollbacks/preplamo-20261112_130956"
PROBE="$STAGE/probe_legacy_api.py"

echo "=== STEP 9AJ-D: ORIGINAL PROBE DIAGNOSTIC ==="
test -x "$DOCKER"
test -f "$PROBE" && test ! -L "$PROBE"
test -r "$BACKUP/image-id.txt"
test -f "$ROOT/app/main.py"
test -d "$ROOT/audio"
test -d "/volume2/docker/japanese-voice-production/voicevox"

# Require exactly the same running image as in archived backup.
sudo -v
original=$(sudo "$DOCKER" inspect --format '{{.Image}}' japanese-api)
test "$original" = "$(cat "$BACKUP/image-id.txt")"
echo "PRODUCTION_IMAGE_MATCH=PASS"

errfile=$(mktemp "$STAGE/9ajdiag_err.XXXXXX")
outfile=$(mktemp "$STAGE/9ajdiag_out.XXXXXX")
trap 'rm -f "$errfile" "$outfile"' EXIT HUP INT TERM

# Same original image and probe as 9AJ, but isolate a fresh empty
# writable temporary DB to avoid a second expensive production backup.
set +e
sudo "$DOCKER" run --rm \
    --network none --read-only \
    --security-opt no-new-privileges \
    --cap-drop ALL --cap-add DAC_OVERRIDE --user 0:0 \
    --tmpfs /tmp:rw,nosuid,nodev,size=32m \
    --tmpfs /srv/data:rw,nosuid,nodev,size=128m,mode=1777 \
    -e PYTHONDONTWRITEBYTECODE=1 \
    -e PYTHONPATH=/srv \
    -v "$ROOT/audio:/srv/audio:ro" \
    -v "/volume2/docker/japanese-voice-production/voicevox:/srv/voicevox-production:ro" \
    -v "$PROBE:/legacy-probe.py:ro" \
    --entrypoint python "$original" /legacy-probe.py \
    >"$outfile" 2>"$errfile"
rc=$?
set -e
echo "ORIGINAL_PROBE_EXIT=$rc"
if [ "$rc" -ne 0 ]; then
    echo "ORIGINAL_PROBE_STDERR_LAST_35_LINES_BEGIN"
    # No auth tokens, secrets or production database ever enter container.
    tail -n 35 "$errfile"
    echo "ORIGINAL_PROBE_STDERR_LAST_35_LINES_END"
    echo "STEP_9AJ_D=DIAGNOSED"
    exit 0
fi

python3 - "$outfile" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        lines = [line for line in fh if line.strip()]
    obj = json.loads(lines[-1])
    print("ORIGINAL_PROBE_ROUTE_COUNT=%s" % len(obj["routes"]))
    for path in ("/healthz", "/api/v1/status", "/api/v1/voices"):
        sample = obj.get("checks", {}).get(path, {})
        print("EMPTY_DB_%s=%s" % (path.replace("/", "_"), sample.get("status", sample.get("error", "UNAVAILABLE"))))
except Exception as exc:
    print("PROBE_OUTPUT_PARSE_FAILED=%s" % type(exc).__name__)
    raise
PY

echo "EMPTY_DB_ORIGINAL_PROBE=PASS"
echo "NOTE=IF_9AJ_FAILED_ONLY_WITH_SQLITE_SNAPSHOT_INSPECT_SNAPSHOT_PERMISSIONS_OR_INIT"
echo "PRODUCTION_SOURCE_MODIFIED=NO"
echo "PRODUCTION_CONTAINER_RESTARTED=NO"
echo "STEP_9AJ_D=PASS"
