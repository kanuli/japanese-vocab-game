#!/usr/bin/env python3
"""9AU — controlled PLaMo translation-only integration on existing HTTPS 8443.

Purpose: mount a tiny PLaMo-only APIRouter into the *exact original* Japanese
API Docker image, leaving original image/source/Compose files untouched on NAS.
One shared API container recreation is unavoidable, but an automatic rollback
recreates it from the pinned original image if ANY post-cutover check fails.

No new WAN ports, no Nginx edits, no full candidate image replacement,
no unrelated API calls, no vocabulary/audio schema migration.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time

ROOT=Path("/volume2/docker/japanese-api")
HOME=Path.home()
DOCKER="/usr/local/bin/docker"
BACKUP=HOME/"japanese-api-rollbacks"/"preplamo-20261112_130956"
STAGED=HOME/"plamo-gateway-staging"/"japanese_api_router.py"
SOCK=HOME/"plamo-gateway-run"/"gateway.sock"
STANDBY="http://127.0.0.1:18015/healthz"
PUBLIC="https://kanu-rustdesk.synology.me:8443"
RESOLVE="kanu-rustdesk.synology.me:8443:127.0.0.1"
SERVICE="japanese-api"
ROOT_IMAGE=None
PROJECT=None
WORK=None
ROLLED_BACK=False
RECREATION_ATTEMPTED=False

def out(key,value):
    print("%s=%s"%(key,value),flush=True)

def run(args,timeout=80,check=True):
    p=subprocess.run(args,text=True,errors="replace",
                     stdin=subprocess.DEVNULL,
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                     timeout=timeout,check=False)
    if check and p.returncode:
        raise RuntimeError("COMMAND_FAILED_"+Path(args[0]).name+"_EXIT_"+str(p.returncode))
    return p

def docker(*args,timeout=80,check=True):
    return run(["sudo","-n",DOCKER]+list(args),timeout=timeout,check=check)

def compose(override,*args,timeout=120):
    cmd=["compose","-p",PROJECT,"-f",str(ROOT/"compose.yaml")]
    if override:cmd+=["-f",str(override)]
    return docker(*(cmd+list(args)),timeout=timeout)

def curl_status(path,post=None,origin=None,options=False,headers_file=None):
    cmd=["curl","-ksS","--connect-timeout","3","--max-time","8",
         "--resolve",RESOLVE,"-o","/dev/null","-w","%{http_code}"]
    if headers_file:cmd+=["-D",str(headers_file)]
    if origin:cmd+=["-H","Origin: "+origin]
    if options:
        cmd+=["-X","OPTIONS",
              "-H","Access-Control-Request-Method: POST",
              "-H","Access-Control-Request-Headers: authorization,content-type"]
    if post is not None:
        cmd+=["-H","Content-Type: application/json","--data",post]
    cmd.append(PUBLIC+path)
    p=run(cmd,timeout=12,check=False)
    return p.stdout.strip() if p.returncode==0 else "UNAVAILABLE"

def direct_health():
    p=run(["curl","-sS","--connect-timeout","2","--max-time","5",
           "-o","/dev/null","-w","%{http_code}",
           "http://127.0.0.1:8015/healthz"],timeout=8,check=False)
    return p.stdout.strip() if p.returncode==0 else "UNAVAILABLE"

def standby_health():
    p=run(["curl","-sS","--connect-timeout","2","--max-time","5",
           "-o","/dev/null","-w","%{http_code}",STANDBY],timeout=8,check=False)
    return p.stdout.strip() if p.returncode==0 else "UNAVAILABLE"

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def original_source_digest():
    with tarfile.open(str(BACKUP/"api-source.tar.gz"),"r:gz") as t:
        f=t.extractfile("app/main.py")
        if f is None:raise RuntimeError("BACKUP_MISSING_MAIN")
        return hashlib.sha256(f.read()).hexdigest()

def docker_inspect(format_string):
    return docker("inspect","--format",format_string,SERVICE).stdout.strip()

def health_poll(label,timeout=55):
    begin=time.monotonic()
    direct="UNAVAILABLE"
    public="UNAVAILABLE"
    while time.monotonic()-begin<timeout:
        running=docker("inspect","--format","{{.State.Running}}",SERVICE,timeout=15,check=False)
        if running.returncode==0 and running.stdout.strip()=="true":
            direct=direct_health()
            if direct=="200":
                public=curl_status("/healthz")
                if public=="200":
                    out(label+"_UPSTREAM_8015","200")
                    out(label+"_HTTPS_8443","200")
                    return
        time.sleep(2)
    out(label+"_UPSTREAM_8015",direct)
    out(label+"_HTTPS_8443",public)
    raise RuntimeError(label+"_HEALTH_FAILED")

def make_compose(path,image,main=None,route=None):
    lines=["services:","  japanese-api:","    image: "+image]
    if main:
        lines+=["    volumes:",
                "      - "+str(main)+":/srv/app/main.py:ro",
                "      - "+str(route)+":/srv/app/plamo_translate_routes.py:ro",
                "      - "+str(SOCK.parent)+":/run/plamo-gateway:ro"]
    path.write_text("\n".join(lines)+"\n",encoding="utf8")
    path.chmod(0o600)

def main():
    global ROOT_IMAGE,PROJECT,WORK,RECREATION_ATTEMPTED
    out("PHASE","9AU_ACTIVATE_PLAMO_TRANSLATION_ONLY")
    required=[ROOT/"compose.yaml",ROOT/"app/main.py",
              BACKUP/"api-source.tar.gz",BACKUP/"image-id.txt",STAGED,SOCK]
    for p in required:
        if not p.exists() or p.is_symlink():
            raise RuntimeError("MISSING_REQUIRED_"+p.name)
    if sha(ROOT/"app/main.py")!=original_source_digest():
        raise RuntimeError("ORIGINAL_MAIN_HAS_CHANGED_STOP")
    src=STAGED.read_text(encoding="utf8")
    if "TRANSLATE_PATH = \"/api/v1/translate/plamo\"" not in src:
        raise RuntimeError("STAGED_ROUTE_NOT_EXPECTED_STOP")
    if "GATEWAY_SOCKET = \"/run/plamo-gateway/gateway.sock\"" not in src:
        raise RuntimeError("STAGED_ROUTE_SOCKET_MISMATCH_STOP")
    os.stat(SOCK)
    if standby_health()!="200":
        raise RuntimeError("PLAMO_STANDBY_NOT_HEALTHY_STOP")
    if curl_status("/healthz")!="200" or direct_health()!="200":
        raise RuntimeError("PRODUCTION_PREHEALTH_NOT_200_STOP")
    out("ORIGINAL_AND_STANDBY_PREHEALTH","PASS")
    subprocess.run(["sudo","-v"],check=True)

    ROOT_IMAGE=docker_inspect("{{.Image}}")
    if ROOT_IMAGE!=(BACKUP/"image-id.txt").read_text().strip():
        raise RuntimeError("ORIGINAL_DOCKER_IMAGE_NOT_RUNNING_STOP")
    if docker_inspect("{{.State.Running}}")!="true":
        raise RuntimeError("PRODUCTION_CONTAINER_STOPPED")
    PROJECT=docker_inspect('{{index .Config.Labels "com.docker.compose.project"}}')
    svc=docker_inspect('{{index .Config.Labels "com.docker.compose.service"}}')
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}",PROJECT) or svc!=SERVICE:
        raise RuntimeError("UNKNOWN_COMPOSE_IDENTITY_STOP")
    if docker_inspect("{{.Config.User}}") not in ("","0","0:0","root"):
        raise RuntimeError("NONROOT_SOCKET_ACCESS_UNVERIFIED_STOP")
    out("ORIGINAL_IMAGE_AND_COMPOSE_LABELS","PASS")

    WORK=HOME/("plamo-translator-live-"+time.strftime("%Y%m%d_%H%M%S"))
    WORK.mkdir(mode=0o700)
    patched=WORK/"main.py"
    orig=ROOT.joinpath("app/main.py").read_text(encoding="utf8")
    old='allow_methods=["GET", "HEAD", "OPTIONS"]'
    if orig.count(old)!=1 or orig.count("app.include_router(voicevox_production_router)")!=1:
        raise RuntimeError("PRODUCTION_MAIN_PATCH_ANCHOR_MISSING_STOP")
    if "plamo_translate_routes" in orig:
        raise RuntimeError("ROUTE_ALREADY_PRESENT_STOP")
    content=orig.replace(old,'allow_methods=["GET", "HEAD", "OPTIONS", "POST"]',1)
    content=content.rstrip()+"\n\nfrom app.plamo_translate_routes import router as plamo_translate_router\napp.include_router(plamo_translate_router)\n"
    patched.write_text(content,encoding="utf8")
    patched.chmod(0o644)
    route=WORK/"plamo_translate_routes.py"
    route.write_text(src,encoding="utf8")
    route.chmod(0o644)
    shutil.copy2(ROOT/"compose.yaml",WORK/"compose.original.yaml")
    out("TRANSLATION_ONLY_PATCH_PREPARED","PASS")

    # Safe Python syntax check without writing __pycache__ into the production
    # application. Parse only the TWO staged files.
    import ast
    ast.parse(patched.read_text(encoding="utf8"))
    ast.parse(route.read_text(encoding="utf8"))
    out("STAGED_PYTHON_SYNTAX","PASS")
    rollback_tag="japanese-api:pre-plamo-9au-"+WORK.name[-15:]
    docker("tag",ROOT_IMAGE,rollback_tag)
    override=WORK/"translation.override.yaml"
    rollback=WORK/"rollback.override.yaml"
    make_compose(override,rollback_tag,patched,route)
    make_compose(rollback,rollback_tag)
    rollback_cmd=WORK/"rollback.sh"
    rollback_cmd.write_text("#!/bin/sh\nset -eu\nsudo "+DOCKER+" compose -p "+
       PROJECT+" -f "+str(ROOT/"compose.yaml")+" -f "+
       str(rollback)+" up -d --no-deps --no-build "+SERVICE+"\n",
       encoding="utf8")
    rollback_cmd.chmod(0o700)
    out("ROLLBACK_SCRIPT",str(rollback_cmd))

    # Verify original Compose + override preserves all other mounts,
    # network, ports, environment, command and original image.
    existing=json.loads(compose(None,"config","--format","json").stdout)["services"][SERVICE]
    candidate=json.loads(compose(override,"config","--format","json").stdout)["services"][SERVICE]
    for key in ("ports","networks","environment","command","entrypoint","user","healthcheck"):
        if existing.get(key)!=candidate.get(key):
            raise RuntimeError("COMPOSE_"+key.upper()+"_CHANGED_STOP")
    def mounts(s):
        d={}
        for m in s.get("volumes",[]):
            if not isinstance(m,dict):
                raise RuntimeError("UNEXPECTED_COMPOSE_VOLUME_FORMAT")
            d[m["target"]]=m
        return d
    origmount=mounts(existing); newmount=mounts(candidate)
    if any(t not in newmount or newmount[t]!=v for t,v in origmount.items()):
        raise RuntimeError("EXISTING_MOUNT_CHANGED_STOP")
    for target in ("/srv/app/main.py","/srv/app/plamo_translate_routes.py","/run/plamo-gateway"):
        if target not in newmount or not newmount[target].get("read_only"):
            raise RuntimeError("NEW_READONLY_MOUNT_MISSING_STOP")
    if candidate.get("image")!=rollback_tag:
        raise RuntimeError("PINNED_IMAGE_NOT_SELECTED_STOP")
    out("SCOPED_COMPOSE_OVERRIDE","PASS")

    # This is the ONE shared API maintenance recreation; no other services.
    # The code is bind mounted onto the original image, not the failed new image.
    out("LIVE_TRANSLATION_CUTOVER","START")
    RECREATION_ATTEMPTED=True
    result=compose(override,"up","-d","--no-deps","--no-build",SERVICE,timeout=150)
    out("DOCKER_RECREATION_EXIT",result.returncode)
    health_poll("NEW",timeout=65)
    current=docker_inspect("{{.Image}}")
    if current!=ROOT_IMAGE:
        raise RuntimeError("IMAGE_CHANGED_UNEXPECTEDLY_STOP")
    out("ORIGINAL_IMAGE_RETAINED","PASS")

    unauth=curl_status("/api/v1/translate/plamo",
        post='{"source_lang":"ja","target_lang":"en","text":"こんにちは"}',
        origin="https://kanuli.github.io")
    out("PLAMO_UNAUTHENTICATED_HTTP",unauth)
    if unauth!="401": raise RuntimeError("PLAMO_UNAUTH_FAILED")
    cors_file=WORK/"preflight.headers"
    cors=curl_status("/api/v1/translate/plamo",
        origin="https://kanuli.github.io",options=True,
        headers_file=cors_file)
    out("PLAMO_CORS_HTTP",cors)
    header=cors_file.read_text(encoding="utf8",errors="replace").lower()
    cors_file.unlink(missing_ok=True)
    if cors not in ("200","204") or \
       "access-control-allow-origin: https://kanuli.github.io" not in header or \
       "access-control-allow-methods:" not in header or "post" not in header:
        raise RuntimeError("PLAMO_CORS_FAILED")
    rejected=curl_status("/api/v1/translate/plamo",
        post='{"source_lang":"ja","target_lang":"en","text":"こんにちは"}',
        origin="https://invalid-origin.example")
    out("PLAMO_BAD_ORIGIN_HTTP",rejected)
    if rejected!="403": raise RuntimeError("PLAMO_ORIGIN_FAILED")

    # Confirm the old service and standby are both still alive.
    if standby_health()!="200": raise RuntimeError("STANDBY_UNHEALTHY")
    if sha(ROOT/"app/main.py")!=original_source_digest():
        raise RuntimeError("ON_DISK_PRODUCTION_SOURCE_CHANGED")
    (WORK/"DEPLOYED_OK").write_text("9AU_OK\n",encoding="utf8")
    out("PRODUCTION_MAIN_AND_COMPOSE_DISK_MODIFIED","NO")
    out("ORIGINAL_IMAGE_IN_USE","YES")
    out("PUBLISHED_8443_PLAMO_API","READY")
    out("GITHUB_PAGES_FRONTEND_PUBLISHED","NO")
    out("STEP_9AU","PASS")


def rollback():
    global ROLLED_BACK
    if not RECREATION_ATTEMPTED or WORK is None or PROJECT is None:
        return
    out("AUTOMATIC_ROLLBACK","START")
    try:
        result=compose(WORK/"rollback.override.yaml",
                       "up","-d","--no-deps","--no-build",SERVICE,timeout=150)
        if result.returncode:
            raise RuntimeError("ROLLBACK_DOCKER_NONZERO")
        health_poll("ROLLBACK",timeout=75)
        if docker_inspect("{{.Image}}")!=ROOT_IMAGE:
            raise RuntimeError("ROLLBACK_IMAGE_MISMATCH")
        ROLLED_BACK=True
        out("AUTOMATIC_ROLLBACK","PASS")
    except Exception:
        out("AUTOMATIC_ROLLBACK","FAILED_MANUAL_ACTION_REQUIRED")
        out("MANUAL_ROLLBACK_SCRIPT",str(WORK/"rollback.sh"))

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        out("STEP_9AU","FAIL")
        out("FAIL_REASON",str(exc)[:220])
        rollback()
        sys.exit(1)
