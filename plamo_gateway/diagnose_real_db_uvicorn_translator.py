#!/usr/bin/env python3
"""Step 9AM: translator-only candidate HTTP startup using a private real SQLite snapshot.

NAS host process:
  - verifies production STILL uses original archived image and HTTP 200
  - opens original SQLite with mode=ro, backs up with SQLite online API
  - starts ONLY disposable networkless container using *copy* of SQLite
  - captures candidate actual Uvicorn HTTP readiness & auth/CORS, no user tokens
  - deletes private backup automatically; never restarts production API

Container child:
  - runs Uvicorn on localhost inside --network none container and probes
    /healthz, unauthenticated /api/v1/translate/plamo, OPTIONS only.
No vocabulary/conjugation/audio API requests are made.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

DOCKER = "/usr/local/bin/docker"
ROOT = Path("/volume2/docker/japanese-api")
DB = ROOT / "data" / "japanese.sqlite3"
HOME = Path.home()
DEST = HOME / "japanese-api-candidates" / "plamo-8443-20261112_141623"
BACKUP = HOME / "japanese-api-rollbacks" / "preplamo-20261112_130956"
CANDIDATE = "japanese-api:plamo-8443-20261112_141623"
SOCKDIR = HOME / "plamo-gateway-run"
THIS = Path(__file__).resolve()
STOP = threading.Event()
FAIL = threading.Event()


def log(s):
    print(s, flush=True)


def sudo_refresh():
    try:
        r = subprocess.run(["sudo", "-n", "-v"],
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL,
                           timeout=7, check=False)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def sudo_heartbeat():
    while not STOP.wait(15):
        if not sudo_refresh():
            FAIL.set()
            return


def gate_sudo():
    if FAIL.is_set() or not sudo_refresh():
        raise RuntimeError("SUDO_AUTH_EXPIRED_STOP_NO_DEPLOY")


def run(args, timeout=140):
    p = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=timeout, check=False)
    if p.returncode:
        log("CHILD_EXIT=%d" % p.returncode)
        log("CHILD_STDERR_LAST_25_LINES_BEGIN")
        for line in p.stderr.splitlines()[-25:]:
            # No bearer token, credentials, env or live DB is supplied.
            log(line[:280])
        log("CHILD_STDERR_LAST_25_LINES_END")
        # Child emits status markers only, not database rows or secrets.
        for line in p.stdout.splitlines()[-12:]:
            if line.startswith(("STEP_9AM=", "STOP_REASON=", "CANDIDATE_", "UVICORN_", "NO_PRODUCTION_", "CONTAINER_")):
                log("CHILD_STDOUT=" + line[:240])
        raise RuntimeError("ISOLATED_CANDIDATE_TEST_FAILED")
    return p.stdout


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def child():
    import uvicorn
    log("CANDIDATE_REAL_DB_UVICORN=START")
    state = {"error": None, "server": None}
    def start():
        try:
            cfg = uvicorn.Config("app.main:app", host="127.0.0.1",
                                 port=18015, log_level="warning",
                                 access_log=False, lifespan="on")
            server = uvicorn.Server(cfg)
            state["server"] = server
            server.run()
        except BaseException as ex:
            state["error"] = type(ex).__name__

    started = time.monotonic()
    worker = threading.Thread(target=start, daemon=True)
    worker.start()
    for step in range(300):
        if state["error"] is not None:
            raise RuntimeError("UVICORN_STARTUP_EXCEPTION_" + state["error"])
        try:
            c = http.client.HTTPConnection("127.0.0.1", 18015, timeout=1)
            c.request("GET", "/healthz")
            r = c.getresponse()
            r.read(2048)
            code = r.status
            c.close()
            if code == 200:
                break
            raise RuntimeError("UVICORN_HEALTH_HTTP_%d" % code)
        except (ConnectionError, OSError):
            time.sleep(0.2)
    else:
        raise RuntimeError("UVICORN_NOT_READY_WITHIN_60SEC")
    log("CANDIDATE_REAL_DB_UVICORN_HTTP200=PASS")
    log("UVICORN_STARTUP_SECONDS=%.2f" % (time.monotonic() - started))

    c = http.client.HTTPConnection("127.0.0.1", 18015, timeout=8)
    c.request("POST", "/api/v1/translate/plamo",
              body='{"source_lang":"ja","target_lang":"en","text":"こんにちは"}'.encode("utf-8"),
              headers={"Content-Type":"application/json",
                       "Origin":"https://kanuli.github.io"})
    r = c.getresponse()
    status = r.status
    r.read(4096)
    c.close()
    if status != 401:
        raise RuntimeError("PLAMO_NO_TOKEN_HTTP_%d" % status)
    log("CANDIDATE_REAL_DB_PLAMO_NO_TOKEN_401=PASS")

    c = http.client.HTTPConnection("127.0.0.1", 18015, timeout=8)
    c.request("OPTIONS", "/api/v1/translate/plamo", headers={
       "Origin": "https://kanuli.github.io",
       "Access-Control-Request-Method": "POST",
       "Access-Control-Request-Headers": "authorization,content-type"})
    r = c.getresponse()
    status = r.status
    origin = r.getheader("Access-Control-Allow-Origin", "")
    methods = r.getheader("Access-Control-Allow-Methods", "")
    r.read(4096)
    c.close()
    if status not in (200, 204) or origin != "https://kanuli.github.io" or "POST" not in methods:
        raise RuntimeError("PLAMO_PREFLIGHT_INVALID_%d" % status)
    log("CANDIDATE_REAL_DB_PLAMO_PREFLIGHT=PASS")

    state["server"].should_exit = True
    worker.join(timeout=4)
    log("NO_PRODUCTION_HTTP_REQUESTS_FROM_CHILD=PASS")
    log("CONTAINER_NETWORK_NONE=PASS")
    log("STEP_9AM_CHILD=PASS")


def host():
    import tarfile
    log("=== STEP 9AM: TRANSLATOR CANDIDATE REAL-DB ISOLATED STARTUP ===")
    for path in (DB, DEST, THIS, BACKUP / "image-id.txt",
                 BACKUP / "api-source.tar.gz", ROOT / "app" / "main.py",
                 ROOT / "audio", SOCKDIR / "gateway.sock",
                 Path("/volume2/docker/japanese-voice-production/voicevox")):
        if not path.exists() or path.is_symlink():
            raise RuntimeError("EXPECTED_PRECONDITION_MISSING_STOP:" + path.name)
    with tarfile.open(str(BACKUP / "api-source.tar.gz"), "r:gz") as t:
        f = t.extractfile("app/main.py")
        if f is None or hashlib.sha256(f.read()).hexdigest() != sha(ROOT / "app" / "main.py"):
            raise RuntimeError("PRODUCTION_SOURCE_NOT_BACKUP_STOP")
    free = shutil.disk_usage(str(DEST)).free
    if free < 2 * DB.stat().st_size + 512 * 1024 * 1024:
        raise RuntimeError("FREE_SPACE_SNAPSHOT_GATE_FAILED")
    log("PRODUCTION_SOURCE_AND_FREE_SPACE=PASS")

    # Only initial sudo -v may request a password. During snapshot keepalive
    # refreshes without prompting and stops if it loses privileges.
    subprocess.run(["sudo", "-v"], check=True)
    gate_sudo()
    image = run(["sudo", "-n", DOCKER, "inspect",
                 "--format", "{{.Image}}", "japanese-api"]).strip()
    if image != (BACKUP / "image-id.txt").read_text().strip():
        raise RuntimeError("ROLLBACK_ORIGINAL_IMAGE_DIFFERENCE_STOP")
    if run(["sudo", "-n", DOCKER, "inspect", "--format",
            "{{.State.Running}}", "japanese-api"]).strip() != "true":
        raise RuntimeError("PRODUCTION_CONTAINER_NOT_RUNNING_STOP")
    run(["sudo", "-n", DOCKER, "image", "inspect", CANDIDATE], timeout=30)
    log("ROLLBACK_ORIGINAL_IMAGE=PASS")
    log("CANDIDATE_IMAGE_PRESENT=PASS")
    check = subprocess.run([
       "curl", "-ksS", "--connect-timeout", "5", "--max-time", "12",
       "--resolve", "kanu-rustdesk.synology.me:8443:127.0.0.1",
       "-o", "/dev/null", "-w", "%{http_code}",
       "https://kanu-rustdesk.synology.me:8443/healthz"],
       text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=16)
    if check.returncode or check.stdout != "200":
        raise RuntimeError("PRODUCTION_8443_ROLLBACK_HEALTH_NOT_200")
    log("PRODUCTION_8443_ROLLBACK_HEALTH=200")

    threading.Thread(target=sudo_heartbeat, daemon=True).start()
    log("SUDO_KEEPALIVE=PASS")
    with tempfile.TemporaryDirectory(dir=str(DEST), prefix="9am-snapshot-") as tmp:
        root = Path(tmp)
        os.chmod(str(root), 0o700)
        dbcopy = root / "japanese.sqlite3"
        uri = "file:" + urllib.parse.quote(str(DB), safe="/") + "?mode=ro"
        src = sqlite3.connect(uri, uri=True, timeout=15)
        try:
            dst = sqlite3.connect(str(dbcopy), timeout=15)
            try:
                log("SQLITE_READONLY_BACKUP=START")
                beginning = time.monotonic()
                last = 0.0
                def progress(status, remaining, total):
                    nonlocal last
                    elapsed = time.monotonic() - beginning
                    if FAIL.is_set():
                        raise RuntimeError("SUDO_KEEPALIVE_FAILED_STOP")
                    if elapsed > 900:
                        raise RuntimeError("SQLITE_BACKUP_TIMEOUT_STOP")
                    if remaining == 0 or elapsed - last >= 20:
                        log("SQLITE_BACKUP_PROGRESS=%.1f%% ELAPSED_SEC=%d" %
                            (100 * (total-remaining)/max(1,total), int(elapsed)))
                        last = elapsed
                src.backup(dst, pages=256, sleep=0.05, progress=progress)
                if dst.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("SNAPSHOT_QUICK_CHECK_FAILED")
            finally:
                dst.close()
        finally:
            src.close()
        os.chmod(str(dbcopy), 0o600)
        log("SQLITE_CONSISTENT_SNAPSHOT_AND_QUICK_CHECK=PASS")
        gate_sudo()
        log("CANDIDATE_REAL_DB_NO_NETWORK_TEST=START")
        cmd=["sudo", "-n", DOCKER, "run", "--rm", "--network", "none",
             "--read-only", "--security-opt", "no-new-privileges",
             "--cap-drop", "ALL", "--cap-add", "DAC_OVERRIDE", "--user", "0:0",
             "--tmpfs", "/tmp:rw,nosuid,nodev,size=32m",
             "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTHONPATH=/srv",
             "-v", str(root)+":/srv/data:rw",
             "-v", str(ROOT / "audio")+":/srv/audio:ro",
             "-v", "/volume2/docker/japanese-voice-production/voicevox:/srv/voicevox-production:ro",
             "-v", str(SOCKDIR)+":/run/plamo-gateway:ro",
             "-v", str(THIS)+":/plamo-9am.py:ro",
             "--entrypoint", "python", CANDIDATE, "/plamo-9am.py", "--child"]
        try:
            out=run(cmd,timeout=130)
        except subprocess.TimeoutExpired:
            # A timed-out docker client can leave behind a disposable
            # container; only remove our uniquely named test, never live API.
            log("DISPOSABLE_CANDIDATE_TIMEOUT=STOP")
            raise
        for line in out.splitlines():
            if line.startswith(("CANDIDATE_", "UVICORN_", "NO_PRODUCTION_", "CONTAINER_", "STEP_9AM_")):
                log(line[:220])
        if "STEP_9AM_CHILD=PASS" not in out:
            raise RuntimeError("CANDIDATE_CHILD_PASS_SIGNAL_MISSING")
        log("CANDIDATE_REAL_DB_NO_NETWORK_TEST=PASS")
    log("TEMP_REAL_DB_SNAPSHOT_REMOVED=PASS")
    gate_sudo()
    after=run(["sudo","-n",DOCKER,"inspect","--format","{{.Image}}","japanese-api"]).strip()
    if after!=image or sha(ROOT/"app"/"main.py")!=hashlib.sha256(
        tarfile.open(str(BACKUP/"api-source.tar.gz"),"r:gz").extractfile("app/main.py").read()
    ).hexdigest():
        raise RuntimeError("PRODUCTION_SOURCE_OR_IMAGE_CHANGED_STOP")
    log("PRODUCTION_IMAGE_AND_SOURCE_UNCHANGED=PASS")
    log("PRODUCTION_CONTAINER_RESTARTED=NO")
    log("NO_FRONTEND_DEPLOY=PASS")
    log("STEP_9AM=PASS")


if __name__ == "__main__":
    try:
        if len(sys.argv)>1 and sys.argv[1]=="--child":
            child()
        else:
            host()
    except Exception as exc:
        log("STEP_9AM=FAIL")
        log("STOP_REASON=%s" % str(exc)[:260])
        sys.exit(1)
    finally:
        STOP.set()
