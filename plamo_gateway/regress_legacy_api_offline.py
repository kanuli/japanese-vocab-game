#!/usr/bin/env python3
"""STEP 9AJ: Offline legacy Japanese API structural/response regression.

This action does NOT change live Japanese API, Docker Compose, Nginx, Gateway,
router, GitHub Pages, or phone settings. Live SQLite is opened mode=ro using
SQLite's online-backup API; each disposable container gets its OWN writable
snapshot. No network, no production database mounts, no live service restarts.

Requires NAS user to run from interactive SSH -tt for sudo Docker privilege.
"""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time
import urllib.parse

DOCKER = "/usr/local/bin/docker"
ROOT = Path("/volume2/docker/japanese-api")
DB = ROOT / "data" / "japanese.sqlite3"
AUDIO = ROOT / "audio"
VOICES = Path("/volume2/docker/japanese-voice-production/voicevox")
HOME = Path.home()
DEST = HOME / "japanese-api-candidates" / "plamo-8443-20261112_141623"
TAG = "japanese-api:plamo-8443-20261112_141623"
BACKUP_DIR = HOME / "japanese-api-rollbacks" / "preplamo-20261112_130956"
STAGING = HOME / "plamo-gateway-staging"
PROBE = STAGING / "probe_legacy_api.py"


def checked(args, **options):
    return subprocess.run(args, check=True, **options)


def sha256_of(path):
    import hashlib
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_probe(image_id, data_path):
    cmd = [
        "sudo", "-n", DOCKER, "run", "--rm",
        "--network", "none", "--read-only",
        "--security-opt", "no-new-privileges",
        "--cap-drop", "ALL", "--cap-add", "DAC_OVERRIDE",
        "--user", "0:0",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=32m",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-e", "PYTHONPATH=/srv",
        "-v", str(data_path) + ":/srv/data:rw",
        "-v", str(AUDIO) + ":/srv/audio:ro",
        "-v", str(VOICES) + ":/srv/voicevox-production:ro",
        "-v", str(PROBE) + ":/legacy-probe.py:ro",
        "--entrypoint", "python", image_id, "/legacy-probe.py",
    ]
    result = checked(cmd, text=True, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, timeout=150)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("EMPTY_PROBE_OUTPUT")
    report = json.loads(lines[-1])
    if not isinstance(report.get("routes"), list) or not isinstance(report.get("checks"), dict):
        raise RuntimeError("INVALID_PROBE_OUTPUT")
    return report


def main():
    print("=== STEP 9AJ: OFFLINE ORIGINAL VS PLAMO CANDIDATE ===", flush=True)
    for p in (DB, AUDIO, VOICES, PROBE,
              DEST, BACKUP_DIR / "api-source.tar.gz",
              BACKUP_DIR / "image-id.txt"):
        if not p.exists() or p.is_symlink():
            raise RuntimeError("EXPECTED_SOURCE_NOT_FOUND_OR_SYMLINK: " + p.name)

    original_main = ROOT / "app" / "main.py"
    if original_main.is_symlink():
        raise RuntimeError("LIVE_MAIN_SYMLINK_STOP")
    # Safety guard identical to earlier candidate smoke; compare with backup.
    import tarfile
    with tarfile.open(str(BACKUP_DIR / "api-source.tar.gz"), "r:gz") as archive:
        backed = archive.extractfile("app/main.py").read()
    import hashlib
    if hashlib.sha256(backed).hexdigest() != sha256_of(original_main):
        raise RuntimeError("SOURCE_DIFFERS_FROM_BACKUP_STOP")
    print("BACKUP_SOURCE_MATCH=PASS", flush=True)

    if not DB.is_file():
        raise RuntimeError("LIVE_DB_NOT_FOUND")
    size = DB.stat().st_size
    free = shutil.disk_usage(str(DEST)).free
    # One consistent backup + two writable copies + conservative reserve.
    if free < 3 * size + 512 * 1024 * 1024:
        raise RuntimeError("INSUFFICIENT_FREE_SPACE_FOR_SNAPSHOT")
    print("SQLITE_SNAPSHOT_SPACE_GATE=PASS", flush=True)

    # Authorization is for Docker access only; never change docker.sock mode.
    checked(["sudo", "-v"])
    original_image = checked([
        "sudo", "-n", DOCKER, "inspect", "--format",
        "{{.Image}}", "japanese-api"
    ], text=True, stdout=subprocess.PIPE).stdout.strip()
    saved = (BACKUP_DIR / "image-id.txt").read_text().strip()
    if original_image != saved or not original_image.startswith("sha256:"):
        raise RuntimeError("PRODUCTION_IMAGE_DIFFERS_FROM_BACKUP_STOP")
    checked(["sudo", "-n", DOCKER, "image", "inspect", TAG],
            stdout=subprocess.DEVNULL)
    print("PRODUCTION_IMAGE_UNCHANGED=PASS", flush=True)
    print("EXISTING_CANDIDATE_IMAGE=PASS", flush=True)

    # TemporaryDirectory removes the user's database-derived copies even if
    # a test fails. Never mount the live production SQLite file in Docker.
    with tempfile.TemporaryDirectory(prefix="regression-", dir=str(DEST)) as d:
        work = Path(d)
        os.chmod(str(work), 0o700)
        snap = work / "master.sqlite3"
        uri = "file:" + urllib.parse.quote(str(DB), safe="/") + "?mode=ro"
        src = sqlite3.connect(uri, uri=True, timeout=15)
        try:
            dst = sqlite3.connect(str(snap), timeout=15)
            try:
                # Print live progress to SSH; the previous script was silent
                # for the full backup and could look hung on a busy WAL.
                total_size = DB.stat().st_size
                print("SQLITE_LIVE_DB_SIZE_MIB=%.1f" %
                      (total_size / (1024 * 1024)), flush=True)
                print("SQLITE_BACKUP=START", flush=True)
                backup_started = time.monotonic()
                last_report = 0.0

                def report_backup(status, remaining, total):
                    nonlocal last_report
                    elapsed = time.monotonic() - backup_started
                    if elapsed > 900:
                        raise TimeoutError(
                            "SQLITE_BACKUP_EXCEEDED_900_SECONDS_STOP")
                    if (elapsed - last_report >= 10 or
                            remaining == 0 or status == sqlite3.SQLITE_BUSY):
                        percent = 100.0 * (total - remaining) / max(1, total)
                        print("SQLITE_BACKUP_PROGRESS=%.1f%% PAGES_LEFT=%s "
                              "ELAPSED_SEC=%d STATUS=%s" %
                              (percent, remaining, int(elapsed), status),
                              flush=True)
                        last_report = elapsed

                src.backup(dst, pages=256, sleep=0.05,
                           progress=report_backup)
                print("SQLITE_BACKUP_COPY=PASS", flush=True)
                print("SQLITE_SNAPSHOT_INTEGRITY_CHECK=START", flush=True)
                status = dst.execute("PRAGMA quick_check").fetchone()[0]
                if status != "ok":
                    raise RuntimeError("SNAPSHOT_INTEGRITY_FAILED")
            finally:
                dst.close()
        finally:
            src.close()
        os.chmod(str(snap), 0o600)
        print("PRODUCTION_SQLITE_OPENED_READONLY=PASS", flush=True)
        print("CONSISTENT_SQLITE_BACKUP=PASS", flush=True)

        reports = {}
        for label, image in (("original", original_image), ("candidate", TAG)):
            data_path = work / label
            data_path.mkdir(mode=0o700)
            copy = data_path / "japanese.sqlite3"
            shutil.copyfile(str(snap), str(copy))
            os.chmod(str(copy), 0o600)
            print("PROBING_%s=START" % label.upper(), flush=True)
            reports[label] = run_probe(image, data_path)
            print("PROBING_%s=PASS" % label.upper(), flush=True)

        baseline = reports["original"]
        candidate = reports["candidate"]
        orig_routes = {(r["path"], tuple(r["methods"])) for r in baseline["routes"]}
        next_routes = {(r["path"], tuple(r["methods"])) for r in candidate["routes"]}
        expected_extra = {
            ("/api/v1/translate/plamo", ("OPTIONS",)),
            ("/api/v1/translate/plamo", ("POST",)),
        }
        missing = orig_routes - next_routes
        extra = next_routes - orig_routes
        print("ORIGINAL_ROUTE_COUNT=%s" % len(orig_routes), flush=True)
        print("CANDIDATE_ROUTE_COUNT=%s" % len(next_routes), flush=True)
        print("MISSING_ORIGINAL_ROUTES=%s" % len(missing), flush=True)
        print("ADDED_ROUTES=%s" % len(extra), flush=True)
        if missing or extra != expected_extra:
            print("UNEXPECTED_ROUTE_DIFF=FAIL", flush=True)
            print("ROUTE_DIFF_MISSING=%s" % sorted(missing), flush=True)
            print("ROUTE_DIFF_ADDED=%s" % sorted(extra), flush=True)
            raise RuntimeError("ROUTE_PARITY_FAILED")
        print("ALL_EXISTING_ROUTES_PRESERVED=PASS", flush=True)

        a = baseline["checks"]
        b = candidate["checks"]
        all_paths = sorted(set(a) | set(b))
        mismatches = [p for p in all_paths if a.get(p) != b.get(p)]
        positive = sum(1 for p in all_paths if a.get(p, {}).get("status") == 200)
        print("SAMPLED_GET_ENDPOINTS=%s" % len(all_paths), flush=True)
        print("SAMPLED_GET_HTTP200=%s" % positive, flush=True)
        print("SAMPLED_GET_MISMATCHES=%s" % len(mismatches), flush=True)
        if mismatches:
            for p in mismatches[:10]:
                print("GET_MISMATCH=%s" % p, flush=True)
            raise RuntimeError("GET_RESPONSE_PARITY_FAILED")
        for p in ("/healthz", "/api/v1/status", "/api/v1/voices"):
            if a.get(p, {}).get("status") != 200:
                raise RuntimeError("CRITICAL_GET_NOT_HTTP200: " + p)
        if positive < 3:
            raise RuntimeError("INSUFFICIENT_POSITIVE_GET_SAMPLES")
        print("SAMPLED_GET_RESPONSE_PARITY=PASS", flush=True)

        # Non-secret audit: only routes, status/size/hash, never actual DB
        # records, text or audio. Preserve summary for subsequent regressions.
        reportfile = DEST / "step9aj-report.json"
        if reportfile.exists() or reportfile.is_symlink():
            raise RuntimeError("REPORT_ALREADY_EXISTS_STOP")
        with open(str(reportfile), "x", encoding="utf-8") as out:
            json.dump({"baseline": baseline, "candidate": candidate},
                      out, indent=2, ensure_ascii=False)
        os.chmod(str(reportfile), 0o600)
        print("REGRESSION_REPORT_SAVED=PASS", flush=True)

    print("TEMP_SQLITE_SNAPSHOTS_REMOVED=PASS", flush=True)
    print("PRODUCTION_SOURCE_UNCHANGED=PASS", flush=True)
    print("PRODUCTION_CONTAINER_RESTARTED=NO", flush=True)
    print("ORIGINAL_GATEWAY_RESTARTED=NO", flush=True)
    print("STEP_9AJ=PASS", flush=True)
    print("NOTE=DYNAMIC_VOCABULARY_AUDIO_CONJUGATION_GET_SAMPLES_NOT_YET_VERIFIED", flush=True)


if __name__ == "__main__":
    main()
