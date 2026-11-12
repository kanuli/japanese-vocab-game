#!/usr/bin/env python3
"""STEP 9AO: translator-only Docker host port reachability canary.

Check 502 cause without touching existing HTTPS 8443/host 8015, Compose,
production SQLite, other API routes, Nginx, Gateway, or frontend.
Launch one disposable candidate with 127.0.0.1:18015:8000, tmpfs data,
then test /healthz and unauthenticated protected translation route only.
"""
import hashlib
import http.client
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tarfile
import time

DOCKER = "/usr/local/bin/docker"
ROOT = Path("/volume2/docker/japanese-api")
HOME = Path.home()
BACKUP = HOME / "japanese-api-rollbacks" / "preplamo-20261112_130956"
TAG = "japanese-api:plamo-8443-20261112_141623"
AUDIO = ROOT / "audio"
VOICEVOX = Path("/volume2/docker/japanese-voice-production/voicevox")
SOCKET_DIR = HOME / "plamo-gateway-run"
HOST_PORT = 18015
PRODUCTION_URL = "https://kanu-rustdesk.synology.me:8443/healthz"
DNS_OVERRIDE = "kanu-rustdesk.synology.me:8443:127.0.0.1"

def say(key, val):
    print("%s=%s" % (key,val), flush=True)

def command(cmd, timeout=30, check=True):
    r = subprocess.run(cmd, stdin=subprocess.DEVNULL,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=timeout, check=False)
    if check and r.returncode != 0:
        raise RuntimeError("COMMAND_EXIT_%d_%s" % (r.returncode, cmd[0].split("/")[-1]))
    return r

def docker(*args, timeout=30, check=True):
    return command(["sudo", "-n", DOCKER] + list(args), timeout, check)

def public_health():
    r = command(["curl","-ksS","--connect-timeout","4","--max-time","10",
                 "--resolve", DNS_OVERRIDE,"-o","/dev/null","-w","%{http_code}",
                 PRODUCTION_URL],timeout=14,check=False)
    return r.stdout.strip() if r.returncode == 0 else "UNAVAILABLE"

def local_get(path):
    c = http.client.HTTPConnection("127.0.0.1", HOST_PORT, timeout=3)
    try:
        c.request("GET",path)
        r = c.getresponse()
        r.read(1024)
        return r.status
    finally:
        c.close()

def local_post(origin):
    c=http.client.HTTPConnection("127.0.0.1",HOST_PORT,timeout=5)
    try:
        body=b'{"source_lang":"ja","target_lang":"en","text":"test"}'
        c.request("POST","/api/v1/translate/plamo", body=body,
                  headers={"Origin":origin,"Content-Type":"application/json"})
        r=c.getresponse()
        r.read(1024)
        return r.status
    finally:
        c.close()

def preflight():
    c=http.client.HTTPConnection("127.0.0.1",HOST_PORT,timeout=5)
    try:
        c.request("OPTIONS","/api/v1/translate/plamo",headers={
          "Origin":"https://kanuli.github.io",
          "Access-Control-Request-Method":"POST",
          "Access-Control-Request-Headers":"authorization,content-type"})
        r=c.getresponse()
        result=(r.status,r.getheader("Access-Control-Allow-Origin"),
                r.getheader("Access-Control-Allow-Methods",""))
        r.read(1024)
        return result
    finally:
        c.close()

def safe_errors(container):
    logs = docker("logs", "--tail", "50", container, check=False)
    lines = (logs.stderr + "\n" + logs.stdout).splitlines()
    errors = [line for line in lines if re.search(
      r"ERROR|Error|Exception|Traceback|Permission denied|bind|failed", line)]
    say("CANARY_LOG_ERROR_COUNT", len(errors))
    for line in errors[-8:]:
        # Avoid echoing arbitrary log content into chat.
        if "authorization" in line.lower() or "token" in line.lower() or "secret" in line.lower():
            continue
        say("CANARY_LOG_ERROR_TYPE", re.findall(
            r"\b[A-Za-z_]+(?:Error|Exception)\b|\b(?:ERROR|failed|denied|bind)\b", line)[:3])

def main():
    say("PHASE","9AO_TRANSLATOR_ONLY_DOCKER_LOCAL_PORT_CANARY")
    required=[BACKUP/"image-id.txt",BACKUP/"api-source.tar.gz",
              ROOT/"app"/"main.py", AUDIO, VOICEVOX,SOCKET_DIR/"gateway.sock"]
    if any(not p.exists() or p.is_symlink() for p in required):
        raise RuntimeError("REQUIRED_BACKUP_OR_MOUNT_MISSING_STOP")
    with tarfile.open(str(BACKUP/"api-source.tar.gz"),"r:gz") as t:
        source=t.extractfile("app/main.py")
        if source is None or hashlib.sha256(source.read()).digest() != hashlib.sha256(
                (ROOT/"app"/"main.py").read_bytes()).digest():
            raise RuntimeError("PRODUCTION_SOURCE_NOT_BACKUP_STOP")
    say("PRODUCTION_MAIN_UNCHANGED","PASS")
    # Reserve-check only; container binds this port after socket closes.
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1",HOST_PORT))
        except OSError:
            raise RuntimeError("LOCAL_CANARY_PORT_18015_BUSY_STOP")
    command(["sudo","-v"],check=True)
    current=docker("inspect","--format","{{.Image}}","japanese-api").stdout.strip()
    if current != (BACKUP/"image-id.txt").read_text().strip():
        raise RuntimeError("PRODUCTION_IMAGE_NOT_ORIGINAL_STOP")
    if docker("inspect","--format","{{.State.Running}}","japanese-api").stdout.strip()!="true":
        raise RuntimeError("PRODUCTION_CONTAINER_NOT_RUNNING_STOP")
    docker("image","inspect",TAG)
    h=public_health()
    say("PUBLIC_8443_BEFORE",h)
    if h!="200":
        raise RuntimeError("PRODUCTION_8443_UNHEALTHY_STOP")
    say("ORIGINAL_IMAGE_RUNNING","PASS")

    name="plamo-translator-9ao-%d-%d" % (os.getpid(),int(time.time()))
    owned_id=None
    try:
        args=["run","-d","--name",name,"--network","bridge",
              "-p","127.0.0.1:%d:8000"%HOST_PORT,
              "--security-opt","no-new-privileges",
              "--cap-drop","ALL","--cap-add","DAC_OVERRIDE",
              "--tmpfs","/tmp:rw,nosuid,nodev,size=32m",
              "--tmpfs","/srv/data:rw,nosuid,nodev,size=128m,mode=1777",
              "-e","PYTHONDONTWRITEBYTECODE=1",
              "-v",str(AUDIO)+":/srv/audio:ro",
              "-v",str(VOICEVOX)+":/srv/voicevox-production:ro",
              "-v",str(SOCKET_DIR)+":/run/plamo-gateway:ro",TAG]
        result=docker(*args,timeout=45,check=False)
        if result.returncode:
            say("CANARY_DOCKER_RUN_EXIT",result.returncode)
            raise RuntimeError("CANARY_DOCKER_RUN_FAILED")
        owned_id=result.stdout.strip()
        if not re.fullmatch(r"[a-f0-9]{64}",owned_id):
            raise RuntimeError("CANARY_CONTAINER_ID_INVALID")
        say("CANARY_IMAGE", "PLaMo_candidate")
        say("CANARY_BIND", "127.0.0.1:18015_only")
        code=None
        for _ in range(36):
            running=docker("inspect","--format","{{.State.Running}}",owned_id,check=False)
            if running.returncode or running.stdout.strip()!="true":
                break
            try:
                code=local_get("/healthz")
                break
            except (OSError, ConnectionError, TimeoutError):
                time.sleep(0.5)
        say("CANARY_HOST_PORT_HEALTH_HTTP",code if code is not None else "NO_RESPONSE")
        if code!=200:
            safe_errors(owned_id)
            raise RuntimeError("CANDIDATE_DOCKER_HOST_PORT_NOT_READY")
        auth=local_post("https://kanuli.github.io")
        say("CANARY_PLAMO_NO_TOKEN_HTTP",auth)
        if auth!=401:
            raise RuntimeError("CANARY_UNAUTH_TRANSLATE_FAIL")
        pf=preflight()
        say("CANARY_PLAMO_PREFLIGHT_HTTP",pf[0])
        if pf[0] not in (200,204) or pf[1]!="https://kanuli.github.io" or "POST" not in pf[2]:
            raise RuntimeError("CANARY_PLAMO_CORS_PREFLIGHT_FAIL")
        origin=local_post("https://invalid-origin.example")
        say("CANARY_BAD_ORIGIN_HTTP",origin)
        if origin!=403:
            raise RuntimeError("CANARY_ORIGIN_REJECTION_FAIL")
    finally:
        if owned_id:
            rm=docker("rm","-f",owned_id,timeout=40,check=False)
            say("TEMP_CANARY_REMOVED","PASS" if rm.returncode==0 else "FAILED_OPERATOR_REVIEW")
            if rm.returncode:
                raise RuntimeError("TEMP_CANARY_CLEANUP_FAILED")

    if docker("inspect","--format","{{.Image}}","japanese-api").stdout.strip()!=current:
        raise RuntimeError("PRODUCTION_IMAGE_CHANGED_STOP")
    say("PRODUCTION_IMAGE_UNCHANGED_AFTER","PASS")
    say("PUBLIC_8443_AFTER",public_health())
    if public_health()!="200":
        raise RuntimeError("PUBLIC_8443_HEALTH_AFTER_NOT_200")
    say("PRODUCTION_CONTAINER_RESTARTED","NO")
    say("PRODUCTION_SQLITE_COPIED_OR_MOUNTED","NO")
    say("NEW_WAN_PORTS","NO")
    say("STEP_9AO","PASS")

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        say("STEP_9AO","FAIL")
        say("STOP_REASON",str(err)[:200])
        sys.exit(1)
