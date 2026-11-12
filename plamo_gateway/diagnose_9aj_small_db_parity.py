#!/usr/bin/env python3
"""9AJ-E: quick exact-image parity and writable small SQLite bind-mount test.

NO production SQLite opened, copied, or mounted. Both tests use distinct,
disposable small databases to diagnose whether 9AJ failed because of the
bind-mount permission / image initialization environment. Network disabled.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile

DOCKER = "/usr/local/bin/docker"
ROOT = Path("/volume2/docker/japanese-api")
HOME = Path.home()
DEST = HOME / "japanese-api-candidates" / "plamo-8443-20261112_141623"
TAG = "japanese-api:plamo-8443-20261112_141623"
BACKUP = HOME / "japanese-api-rollbacks" / "preplamo-20261112_130956"
PROBE = HOME / "plamo-gateway-staging" / "probe_legacy_api.py"
AUDIO = ROOT / "audio"
VOICEVOX = Path("/volume2/docker/japanese-voice-production/voicevox")

def emit(s):
    print(s, flush=True)

def run(args, capture=True, timeout=105):
    try:
        r = subprocess.run(args, text=True, check=False,
                           stdout=subprocess.PIPE if capture else None,
                           stderr=subprocess.PIPE if capture else None,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError("DOCKER_TEST_TIMEOUT_STOP")
    if r.returncode:
        emit("DOCKER_EXIT_CODE=%d" % r.returncode)
        emit("DOCKER_STDERR_LAST_22_LINES_BEGIN")
        for line in (r.stderr or "").splitlines()[-22:]:
            emit(line[:240])
        emit("DOCKER_STDERR_LAST_22_LINES_END")
        raise RuntimeError("DOCKER_DISPOSABLE_PROBE_FAILED")
    return (r.stdout or "")

def before():
    emit("=== STEP 9AJ-E: SMALL SQLITE BIND + ROUTE PARITY ===")
    for p in (DEST, PROBE, ROOT / "app" / "main.py",
              BACKUP / "image-id.txt", BACKUP / "api-source.tar.gz",
              AUDIO, VOICEVOX):
        if not p.exists() or p.is_symlink():
            raise RuntimeError("PRECONDITION_PATH_UNAVAILABLE_STOP:" + p.name)
    with tarfile.open(str(BACKUP / "api-source.tar.gz"), "r:gz") as tar:
        f = tar.extractfile("app/main.py")
        if f is None:
            raise RuntimeError("BACKUP_MAIN_MISSING")
        expected = hashlib.sha256(f.read()).hexdigest()
    actual = hashlib.sha256((ROOT / "app" / "main.py").read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError("LIVE_MAIN_DIFFERS_FROM_BACKUP_STOP")
    emit("BACKUP_SOURCE_MATCH=PASS")
    # sudo -v is interactive through ssh -tt, then -n for diagnostics.
    subprocess.run(["sudo", "-v"], check=True)
    current = run(["sudo", "-n", DOCKER, "inspect", "--format",
                   "{{.Image}}", "japanese-api"]).strip()
    saved = (BACKUP / "image-id.txt").read_text().strip()
    if current != saved or not current.startswith("sha256:"):
        raise RuntimeError("PRODUCTION_IMAGE_DIFFERENCE_STOP")
    run(["sudo", "-n", DOCKER, "image", "inspect", TAG])
    emit("PRODUCTION_IMAGE_MATCH=PASS")
    emit("CANDIDATE_IMAGE_PRESENT=PASS")
    return current

def one(image, data_dir, label):
    # Reproduce 9AJ's EXACT readonly-root / rw bind mount conditions with
    # tiny scratch DB; root+DAC_OVERRIDE is solely for the disposable probe.
    cmd = [
        "sudo", "-n", DOCKER, "run", "--rm", "--network", "none",
        "--read-only", "--security-opt", "no-new-privileges",
        "--cap-drop", "ALL", "--cap-add", "DAC_OVERRIDE",
        "--user", "0:0", "--tmpfs", "/tmp:rw,nosuid,nodev,size=32m",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTHONPATH=/srv",
        "-v", str(data_dir) + ":/srv/data:rw",
        "-v", str(AUDIO) + ":/srv/audio:ro",
        "-v", str(VOICEVOX) + ":/srv/voicevox-production:ro",
        "-v", str(PROBE) + ":/legacy-probe.py:ro",
        "--entrypoint", "python", image, "/legacy-probe.py",
    ]
    stdout = run(cmd)
    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("EMPTY_PROBE_RESULT:" + label)
    try:
        result = json.loads(lines[-1])
    except (ValueError, IndexError):
        raise RuntimeError("MALFORMED_PROBE_OUTPUT:" + label)
    routes = result.get("routes")
    checks = result.get("checks")
    if not isinstance(routes, list) or not isinstance(checks, dict):
        raise RuntimeError("UNEXPECTED_PROBE_SCHEMA")
    emit("%s_PROBE_EXIT=0" % label.upper())
    emit("%s_ROUTE_COUNT=%d" % (label.upper(), len(routes)))
    emit("%s_HEALTHZ=%s" %
         (label.upper(), checks.get("/healthz", {}).get("status", "N/A")))
    return result

def main():
    original = before()
    with tempfile.TemporaryDirectory(dir=str(DEST),
                                     prefix="9aje-small-") as temp:
        workspace = Path(temp)
        os.chmod(str(workspace), 0o700)
        reports = {}
        for label, image in (("original", original), ("candidate", TAG)):
            data_dir = workspace / label
            data_dir.mkdir(mode=0o700)
            db = data_dir / "japanese.sqlite3"
            conn = sqlite3.connect(str(db))
            conn.execute("CREATE TABLE IF NOT EXISTS regression_canary (k TEXT)")
            conn.commit()
            conn.close()
            os.chmod(str(db), 0o600)
            emit("START_%s_SMALL_DB_PROBE" % label.upper())
            reports[label] = one(image, data_dir, label)
            emit("%s_SMALL_DB_BIND=PASS" % label.upper())

        a, b = reports["original"], reports["candidate"]
        r1 = {(r["path"], tuple(sorted(r.get("methods", []))))
              for r in a["routes"]}
        r2 = {(r["path"], tuple(sorted(r.get("methods", []))))
              for r in b["routes"]}
        missing, added = r1 - r2, r2 - r1
        emit("MISSING_ORIGINAL_ROUTES=%d" % len(missing))
        emit("ADDED_ROUTES=%d" % len(added))
        expected = {
            ("/api/v1/translate/plamo", ("OPTIONS",)),
            ("/api/v1/translate/plamo", ("POST",)),
        }
        if missing or added != expected:
            emit("MISSING_ROUTES=%s" % sorted(missing))
            emit("EXTRA_ROUTES=%s" % sorted(added))
            raise RuntimeError("STRUCTURAL_ROUTE_PARITY_FAILED")
        emit("ALL_ORIGINAL_ROUTES_PRESERVED=PASS")
        if a["checks"].get("/healthz", {}).get("status") != 200:
            raise RuntimeError("ORIGINAL_HEALTH_NOT_200")
        if b["checks"].get("/healthz", {}).get("status") != 200:
            raise RuntimeError("CANDIDATE_HEALTH_NOT_200")
        emit("ORIGINAL_AND_CANDIDATE_HEALTH=PASS")
        # Incomplete empty-db legacy status/voices is expected and NOT a
        # production test. Compare only route structure and healthy startup.
        emit("STEP_9AJ_E=PASS")
        emit("WARNING=REAL_DATA_STATUS_VOICES_AUDIO_CONJUGATION_NOT_VALIDATED")
    emit("TEMP_SMALL_SQLITE_REMOVED=PASS")
    if hashlib.sha256((ROOT / "app" / "main.py").read_bytes()).hexdigest() != expected:
        raise RuntimeError("PRODUCTION_SOURCE_MODIFIED_STOP")
    emit("PRODUCTION_SOURCE_UNCHANGED=PASS")
    emit("PRODUCTION_CONTAINER_RESTARTED=NO")
    emit("ORIGINAL_GATEWAY_RESTARTED=NO")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit("STEP_9AJ_E=FAIL")
        emit("STOP_REASON=%s" % str(exc)[:400])
        sys.exit(1)
