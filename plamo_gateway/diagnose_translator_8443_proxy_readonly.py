#!/usr/bin/env python3
"""STEP 9AP — read-only effective 8443 proxy/upstream inspection.

NO deploy/restart/write. Neither Nginx configuration, Docker service, NAS
database, translator source, nor any other Japanese learning page is touched.
Never print Nginx full configuration or Compose environment/secrets.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse

ROOT = Path("/volume2/docker/japanese-api")
HOME = Path.home()
BACKUP = HOME / "japanese-api-rollbacks" / "preplamo-20261112_130956"
DOCKER = "/usr/local/bin/docker"
ORIGINAL_API = "japanese-api"
CANDIDATE = "japanese-api:plamo-8443-20261112_141623"
HTTPS = "https://kanu-rustdesk.synology.me:8443/healthz"
RESOLVE = "kanu-rustdesk.synology.me:8443:127.0.0.1"

def say(name, value):
    print("%s=%s" % (name, value), flush=True)

def cmd(args, timeout=25, check=True):
    proc = subprocess.run(args, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, errors="replace",
                          timeout=timeout, check=False)
    if check and proc.returncode:
        raise RuntimeError("COMMAND_FAILED_%s_%d" %
                           (Path(args[0]).name, proc.returncode))
    return proc

def docker(*args):
    return cmd(["sudo", "-n", DOCKER] + list(args))

def status(url, override=None):
    args = ["curl", "-ksS", "--connect-timeout", "4",
            "--max-time", "12", "-o", "/dev/null",
            "-w", "%{http_code}"]
    if override:
        args.extend(["--resolve", override])
    args.append(url)
    p=cmd(args, timeout=16, check=False)
    return p.stdout.strip() if p.returncode == 0 else "UNAVAILABLE"

def classify_endpoint(value):
    value=value.strip().strip("'\"")
    m=re.match(r"(?i)^(?:(?:https?:)?//)?([^/:;]+)(?::([0-9]{1,5}))?", value)
    if not m:
        return "UNKNOWN", "unknown"
    host=m.group(1).strip("[]")
    port=m.group(2) or "default"
    if host in ("127.0.0.1", "localhost", "::1"):
        group="HOST_LOOPBACK"
    elif host.startswith("$"):
        group="NGINX_VARIABLE"
    elif host.startswith("unix:"):
        group="UNIX_SOCKET"
    elif re.fullmatch(r"[0-9]{1,3}(?:\.[0-9]{1,3}){3}", host):
        group="IP_ADDRESS"
    else:
        group="HOSTNAME_OR_UPSTREAM_NAME"
    return group,port

def nginx_blocks(s):
    # nginx -T is parsed IN MEMORY only. Strings/values not printed.
    stack=[]
    start=0
    results=[]
    # Filter to tokens that matter; braces may appear in regex locations,
    # so non-parser output remains advisory, never enough to deploy.
    for m in re.finditer(r"\bserver\s*\{|[{}]", s):
        tok=m.group()
        if tok.startswith("server") and tok.endswith("{"):
            stack.append(("server",m.end()))
        elif tok=="{":
            stack.append(("other",m.end()))
        elif tok=="}" and stack:
            kind,idx=stack.pop()
            if kind=="server":
                results.append(s[idx:m.start()])
    return results

def inspect_nginx():
    options=[
        shutil.which("nginx"),
        "/usr/syno/bin/nginx",
        "/usr/syno/sbin/nginx",
        "/usr/sbin/nginx",
        "/usr/local/nginx/sbin/nginx",
    ]
    seen=set()
    for nginx in options:
        if not nginx or nginx in seen or not Path(nginx).exists():
            continue
        seen.add(nginx)
        for args in (["-T"],):
            p=cmd(["sudo","-n",nginx]+args, timeout=20, check=False)
            if p.returncode != 0 or not p.stdout.strip():
                continue
            s=p.stdout
            blocks=[b for b in nginx_blocks(s)
                    if re.search(r"\blisten\s+[^;]*\b8443\b", b)]
            if not blocks:
                say("NGINX_8443_LISTEN_BLOCK", "NOT_LOCATED")
                return
            say("NGINX_8443_LISTEN_BLOCKS", len(blocks))
            for i,block in enumerate(blocks[:3]):
                # Report sanitized target class, not raw directives or domains.
                matches=re.findall(r"\bproxy_pass\s+([^;\s]+)",block)
                say("NGINX_8443_BLOCK_%d_PROXY_COUNT" % i,len(matches))
                for j,target in enumerate(matches[:8]):
                    group,port=classify_endpoint(target)
                    say("NGINX_8443_PROXY_%d_%d" % (i,j),
                        "%s:PORT_%s" % (group,port))
                if not matches:
                    say("NGINX_8443_BLOCK_%d_PROXY" % i,
                        "NONE_OR_INCLUDE_INDIRECTION")
            return
    say("NGINX_8443_PROXY_INSPECTION","UNAVAILABLE_NO_CONFIG_DUMP")
    # No hard error; output makes limitation explicit.

def main():
    say("PHASE","9AP_TRANSLATOR_ONLY_8443_PROXY_READONLY")
    paths=[ROOT/"app"/"main.py", BACKUP/"api-source.tar.gz",
           BACKUP/"image-id.txt"]
    if any(not p.is_file() or p.is_symlink() for p in paths):
        raise RuntimeError("SOURCE_OR_BACKUP_MISSING_STOP")
    with tarfile.open(str(paths[1]),"r:gz") as t:
        f=t.extractfile("app/main.py")
        if f is None or hashlib.sha256(f.read()).hexdigest()!=hashlib.sha256(
                paths[0].read_bytes()).hexdigest():
            raise RuntimeError("SOURCE_CHANGED_STOP")
    say("ORIGINAL_SOURCE_CHECK","PASS")
    subprocess.run(["sudo","-v"],check=True)
    image=docker("inspect","--format","{{.Image}}",ORIGINAL_API).stdout.strip()
    if image!=(BACKUP/"image-id.txt").read_text().strip():
        raise RuntimeError("PRODUCTION_IMAGE_NOT_ORIGINAL_STOP")
    if docker("inspect","--format","{{.State.Running}}",ORIGINAL_API).stdout.strip()!="true":
        raise RuntimeError("PRODUCTION_CONTAINER_NOT_RUNNING_STOP")
    say("ORIGINAL_IMAGE_STILL_RUNNING","PASS")
    before=status(HTTPS,RESOLVE)
    direct=status("http://127.0.0.1:8015/healthz")
    say("PUBLIC_8443_BEFORE",before)
    say("UPSTREAM_8015_BEFORE",direct)
    if before!="200" or direct!="200":
        raise RuntimeError("EXISTING_HEALTH_NOT_200_STOP")
    image_config=json.loads(docker("inspect",ORIGINAL_API).stdout)[0]
    hostports=image_config["NetworkSettings"]["Ports"]
    mapping=hostports.get("8000/tcp") or []
    ports=sorted({str(m.get("HostPort")) for m in mapping})
    say("ACTUAL_DOCKER_8000_PUBLISHED_HOST_PORTS",",".join(ports) or "NONE")
    say("ACTUAL_DOCKER_8000_TO_8015","YES" if "8015" in ports else "NO")
    hostips=sorted({str(m.get("HostIp")) for m in mapping})
    say("ACTUAL_DOCKER_BIND_KIND",
        "ALL_INTERFACES" if "0.0.0.0" in hostips or "::" in hostips else
        "LOOPBACK" if "127.0.0.1" in hostips else "OTHER")
    net=image_config.get("NetworkSettings",{}).get("Networks") or {}
    say("ORIGINAL_CONTAINER_NETWORK_COUNT",len(net))
    inspect_nginx()
    after=status(HTTPS,RESOLVE)
    say("PUBLIC_8443_AFTER",after)
    if after!="200":
        raise RuntimeError("PUBLIC_HEALTH_CHANGED_STOP")
    if docker("inspect","--format","{{.Image}}",ORIGINAL_API).stdout.strip()!=image:
        raise RuntimeError("PRODUCTION_IMAGE_CHANGED_DURING_INSPECTION_STOP")
    say("PRODUCTION_IMAGE_UNCHANGED","PASS")
    say("PRODUCTION_CONTAINER_RESTARTED","NO")
    say("PRODUCTION_SQLITE_OPENED","NO")
    say("NGINX_CONFIG_MODIFIED","NO")
    say("NEW_DOCKER_CONTAINER_CREATED","NO")
    say("STEP_9AP","PASS")

if __name__=="__main__":
    try:
        main()
    except Exception as err:
        say("STEP_9AP","FAIL")
        say("STOP_REASON",str(err)[:210])
        sys.exit(1)
