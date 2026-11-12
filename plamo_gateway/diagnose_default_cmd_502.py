#!/usr/bin/env python3
"""9AN - Diagnose translator-only HTTP 502 without another live cutover.

Compares running original Compose metadata with staged candidate override,
then runs each exact image using its *default ENTRYPOINT/CMD* in a disposable
network-disabled container with empty tmpfs DB and no production DB mount.
Does not change production Compose, image, database, Gateway, Nginx or Pages.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import time
import urllib.parse

DOCKER = "/usr/local/bin/docker"
ROOT = Path("/volume2/docker/japanese-api")
BACKUP = Path.home() / "japanese-api-rollbacks" / "preplamo-20261112_130956"
FAILED = Path.home() / "plamo-translation-deploy-20261112_200806"
TAG = "japanese-api:plamo-8443-20261112_141623"
SOCKDIR = Path.home() / "plamo-gateway-run"
URL = "https://kanu-rustdesk.synology.me:8443/healthz"
RESOLVE = "kanu-rustdesk.synology.me:8443:127.0.0.1"


def emit(key, value):
    print("%s=%s" % (key, value), flush=True)


def run(args, timeout=60, check=True):
    p = subprocess.run(args, text=True, encoding="utf-8",
                       errors="replace", stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=timeout, check=False)
    if check and p.returncode:
        raise RuntimeError("COMMAND_FAILED:" + str(args[:3]) + ":EXIT_" + str(p.returncode))
    return p


def docker(*args, timeout=40, check=True):
    return run(["sudo", "-n", DOCKER] + list(args), timeout=timeout, check=check)


def health():
    p = run(["curl", "-ksS", "--connect-timeout", "4", "--max-time", "9",
             "--resolve", RESOLVE, "-o", "/dev/null", "-w", "%{http_code}", URL], timeout=13, check=False)
    return p.stdout.strip() if p.returncode == 0 else "UNAVAILABLE"


def image_meta(img):
    p = docker("image", "inspect", img)
    v = json.loads(p.stdout)[0]["Config"]
    return {
        "user": v.get("User") or "",
        "entrypoint": v.get("Entrypoint") or [],
        "cmd": v.get("Cmd") or [],
        "working_dir": v.get("WorkingDir") or "",
    }


def compose_meta(project, files):
    p = docker("compose", "-p", project, *sum([["-f", f] for f in files], []),
               "config", "--format", "json")
    # Parse JSON in memory; never print Compose environment values.
    obj = json.loads(p.stdout)
    return obj["services"]["japanese-api"]


def mount_targets(obj):
    r = set()
    for m in obj.get("volumes", []):
        r.add(m.get("target") if isinstance(m, dict) else m.split(":")[1])
    return r


def docker_ready(cname):
    # Compare true image CMD startup, not custom Uvicorn test override.
    code = ('import http.client,sys;'
            'c=http.client.HTTPConnection("127.0.0.1",8000,timeout=2);'
            'c.request("GET","/healthz");'
            'r=c.getresponse();r.read(2048);'
            'print(r.status);c.close()')
    p = docker("exec", cname, "python", "-c", code, timeout=7, check=False)
    return p.returncode == 0 and p.stdout.strip() == "200"


def diagnostic(container, label):
    log = docker("logs", "--tail", "45", container, timeout=10, check=False)
    lines = (log.stderr + "\n" + log.stdout).splitlines()
    # Display only exception/ERROR summaries: no request bodies, secrets,
    # log headers, environment values, or internal IPs.
    matches = [s for s in lines if re.search(
        r"Traceback|Error:|ERROR:|Exception|address already in use|Permission denied|ModuleNotFoundError", s)]
    emit(label + "_ERROR_LINES", len(matches))
    for line in matches[-8:]:
        cleaned = re.sub(r"(?i)(token|secret|password|api_key|authorization)\s*[:=]\s*\S+",
                         r"\1=[REDACTED]", line)
        emit(label + "_ERROR", cleaned.strip()[:200])


def one(image, label, audio, voices):
    name = "plamo-9an-%s-%d-%d" % (label.lower(), os.getpid(), int(time.time()))
    # Never remove a container unless its ID was returned by our run.
    container = None
    try:
        args = ["run", "-d", "--name", name, "--network", "none",
                "--security-opt", "no-new-privileges",
                "--tmpfs", "/tmp:rw,nosuid,nodev,size=32m",
                "--tmpfs", "/srv/data:rw,nosuid,nodev,size=128m,mode=1777",
                "-e", "PYTHONDONTWRITEBYTECODE=1",
                "-v", "%s:/srv/audio:ro" % audio,
                "-v", "%s:/srv/voicevox-production:ro" % voices]
        if label == "CANDIDATE":
            args += ["-v", "%s:/run/plamo-gateway:ro" % SOCKDIR]
        args += [image]
        p = docker(*args, timeout=35, check=False)
        if p.returncode:
            emit(label + "_DEFAULT_CMD_DOCKER_RUN_EXIT", p.returncode)
            for line in p.stderr.splitlines()[-4:]:
                emit(label + "_DOCKER_ERROR", line[:160])
            raise RuntimeError(label + "_DEFAULT_CMD_DOCKER_RUN_FAILED")
        container = p.stdout.strip()
        if not re.fullmatch("[a-f0-9]{64}", container):
            raise RuntimeError("CONTAINER_ID_INVALID")
        healthy = False
        for i in range(25):
            ps = docker("inspect", "--format", "{{.State.Running}}", container, check=False)
            if ps.returncode or ps.stdout.strip() != "true":
                break
            if docker_ready(container):
                healthy = True
                break
            time.sleep(1)
        if not healthy:
            diagnostic(container, label)
            state = docker("inspect", "--format",
                           "{{.State.Status}}:{{.State.ExitCode}}", container, check=False)
            emit(label + "_CONTAINER_STATE", state.stdout.strip()[:60] if state.returncode == 0 else "UNKNOWN")
            raise RuntimeError(label + "_DEFAULT_CMD_NOT_HEALTHY")
        emit(label + "_DEFAULT_CMD_HTTP_8000", 200)
    finally:
        if container:
            docker("rm", "-f", container, timeout=20, check=False)
            emit(label + "_TEMP_CONTAINER_REMOVED", "PASS")


def main():
    emit("PHASE", "9AN_TRANSLATOR_ONLY_COMPOSE_502_DIAGNOSTIC")
    for p in [ROOT / "compose.yaml", ROOT / "app" / "main.py",
              BACKUP / "api-source.tar.gz", BACKUP / "image-id.txt",
              FAILED / "plamo.override.yaml", SOCKDIR / "gateway.sock",
              ROOT / "audio", Path("/volume2/docker/japanese-voice-production/voicevox")]:
        if not p.exists() or p.is_symlink():
            raise RuntimeError("EXPECTED_PATH_NOT_FOUND_OR_SYMLINK:" + p.name)
    with tarfile.open(str(BACKUP / "api-source.tar.gz"), "r:gz") as t:
        f = t.extractfile("app/main.py")
        if f is None:
            raise RuntimeError("BACKUP_MAIN_MISSING")
        saved_hash = hashlib.sha256(f.read()).hexdigest()
    actual_hash = hashlib.sha256((ROOT / "app" / "main.py").read_bytes()).hexdigest()
    if actual_hash != saved_hash:
        raise RuntimeError("PRODUCTION_SOURCE_MODIFIED_STOP")
    emit("PRODUCTION_MAIN_UNCHANGED", "PASS")
    # Auth only for permission to run Docker diagnostics, not change live service.
    subprocess.run(["sudo", "-v"], check=True)
    current = docker("inspect", "--format", "{{.Image}}", "japanese-api").stdout.strip()
    expected = (BACKUP / "image-id.txt").read_text().strip()
    if current != expected:
        raise RuntimeError("ROLLBACK_IMAGE_NOT_ORIGINAL_STOP")
    emit("PRODUCTION_ORIGINAL_IMAGE", "PASS")
    live = health()
    emit("PUBLIC_8443_HEALTH_BEFORE", live)
    if live != "200":
        raise RuntimeError("PRODUCTION_HEALTH_NOT_200_STOP")
    proj = docker("inspect", "--format",
                  '{{index .Config.Labels "com.docker.compose.project"}}',
                  "japanese-api").stdout.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", proj):
        raise RuntimeError("UNTRUSTED_COMPOSE_PROJECT")
    base = compose_meta(proj, [str(ROOT / "compose.yaml")])
    cand = compose_meta(proj, [str(ROOT / "compose.yaml"),
                               str(FAILED / "plamo.override.yaml")])
    a = mount_targets(base)
    b = mount_targets(cand)
    emit("COMPOSE_ORIGINAL_PORTS_PRESENT", bool(base.get("ports")))
    emit("COMPOSE_CANDIDATE_PORTS_PRESERVED", base.get("ports") == cand.get("ports"))
    emit("COMPOSE_CANDIDATE_NETWORK_PRESERVED", base.get("networks") == cand.get("networks"))
    emit("COMPOSE_CANDIDATE_ENV_PRESERVED", base.get("environment") == cand.get("environment"))
    emit("COMPOSE_CANDIDATE_MISSING_OLD_MOUNTS", len(a - b))
    emit("COMPOSE_CANDIDATE_SOCKET_MOUNT", "/run/plamo-gateway" in b)
    emit("COMPOSE_APP_CODE_OVERMOUNT", any(x in b for x in ("/srv","/srv/app","/srv/app/main.py")))
    emit("COMPOSE_EFFECTIVE_USER", repr(str(cand.get("user") or "<image-default>"))[:85])
    emit("COMPOSE_BUILD_PRESENT", bool(cand.get("build")))
    meta0 = image_meta(current)
    meta1 = image_meta(TAG)
    emit("CANDIDATE_DEFAULT_CMD_MATCHES_ORIGINAL", meta0["cmd"] == meta1["cmd"])
    emit("CANDIDATE_ENTRYPOINT_MATCHES_ORIGINAL", meta0["entrypoint"] == meta1["entrypoint"])
    emit("CANDIDATE_WORKDIR_MATCHES_ORIGINAL", meta0["working_dir"] == meta1["working_dir"])
    emit("CANDIDATE_USER_MATCHES_ORIGINAL", meta0["user"] == meta1["user"])
    # Exact image default CMD test, with new networkless disposable containers.
    one(current, "ORIGINAL", ROOT / "audio",
        "/volume2/docker/japanese-voice-production/voicevox")
    one(TAG, "CANDIDATE", ROOT / "audio",
        "/volume2/docker/japanese-voice-production/voicevox")
    if docker("inspect", "--format", "{{.Image}}", "japanese-api").stdout.strip() != current:
        raise RuntimeError("PRODUCTION_IMAGE_CHANGED_STOP")
    emit("PRODUCTION_IMAGE_UNCHANGED_AFTER", "PASS")
    emit("PUBLIC_8443_HEALTH_AFTER", health())
    emit("LIVE_JAPANESE_API_RESTARTED", "NO")
    emit("NEW_WAN_PORTS", "NO")
    emit("STEP_9AN", "PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit("STEP_9AN", "FAIL")
        emit("STOP_REASON", str(exc)[:220])
        sys.exit(1)
