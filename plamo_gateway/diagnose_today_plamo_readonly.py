#!/usr/bin/env python3
"""Read-only diagnosis of shared PLaMo availability across devices.

No secrets, authenticated requests, model inference, database access, NAS
configuration edits, docker changes or process restarts.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

API_HOST="kanu-rustdesk.synology.me"
URL="https://"+API_HOST+":8443"
WINDOWS_BRIDGE="http://192.168.1.13:18789/healthz"
UDS=Path.home()/"plamo-gateway-run"/"gateway.sock"
DOCKER="/usr/local/bin/docker"
ORIGIN="https://kanuli.github.io"

def emit(k,v):
    print(k+"="+str(v),flush=True)

def call(args,timeout=12):
    try:
        return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              stdin=subprocess.DEVNULL,timeout=timeout,check=False,
                              text=True,errors="replace")
    except (subprocess.TimeoutExpired,OSError):
        return None

def http(url,method="GET",post=None,local_https=False,origin=None):
    cmd=["curl","-ksS","--connect-timeout","3","--max-time","8",
         "-o","/dev/null","-w","%{http_code}"]
    if local_https:
        cmd+=["--resolve",API_HOST+":8443:127.0.0.1"]
    if origin:
        cmd+=["-H","Origin: "+origin]
    if method!="GET":
        cmd+=["-X",method]
    if post is not None:
        cmd+=["-H","Content-Type: application/json","--data",post]
    cmd.append(url)
    r=call(cmd,11)
    return r.stdout.strip() if r and r.returncode==0 else "UNREACHABLE"

def socket_health():
    if not UDS.is_socket():
        return "SOCKET_MISSING"
    b=b""
    x=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    x.settimeout(4)
    try:
        x.connect(str(UDS))
        x.sendall(b"GET /healthz HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
        b=x.recv(256)
    except Exception:
        return "NOT_RESPONDING"
    finally:
        x.close()
    if b" 200 " in b[:32]:return "200"
    return "NOT_200"

def docker_state():
    r=call(["sudo","-n",DOCKER,"inspect",
            "--format","{{json .Mounts}}","japanese-api"],10)
    if not r or r.returncode:return "UNAVAILABLE",[]
    try:
        mounts=json.loads(r.stdout)
        targets=[str(x.get("Destination","")) for x in mounts]
        return "AVAILABLE",targets
    except (ValueError,TypeError):
        return "UNPARSEABLE",[]

def main():
    emit("PHASE","TODAY_PLAMO_ONLY_READONLY")
    emit("PUBLIC_8443_HEALTH",http(URL+"/healthz",local_https=True))
    body='{"source_lang":"ja","target_lang":"en","text":"こんにちは"}'
    route=http(URL+"/api/v1/translate/plamo",
               method="POST",post=body,local_https=True,origin=ORIGIN)
    emit("PUBLIC_PLAMO_NO_TOKEN_HTTP",route)
    emit("DIRECT_8015_HEALTH",http("http://127.0.0.1:8015/healthz"))
    direct_route=http("http://127.0.0.1:8015/api/v1/translate/plamo",
                      method="POST",post=body,origin=ORIGIN)
    emit("DIRECT_8015_PLAMO_NO_TOKEN_HTTP",direct_route)
    emit("STANDBY_18015_HEALTH",http("http://127.0.0.1:18015/healthz"))
    emit("PRIVATE_GATEWAY_UDS_HEALTH",socket_health())
    emit("NAS_TO_WINDOWS_18789_HEALTH",http(WINDOWS_BRIDGE))
    d,mounts=docker_state()
    emit("DOCKER_INSPECT",d)
    for label,target in [
        ("LIVE_TRANSLATOR_ROUTER_MOUNT","/srv/app/plamo_translate_routes.py"),
        ("LIVE_TRANSLATOR_MAIN_MOUNT","/srv/app/main.py"),
        ("LIVE_GATEWAY_SOCKET_MOUNT","/run/plamo-gateway")
    ]:
        emit(label, "YES" if target in mounts else "NO" if d=="AVAILABLE" else "UNKNOWN")

    if route=="404" and direct_route=="404":
        emit("LIKELY_CAUSE","TRANSLATOR_ROUTE_MISSING_IN_LIVE_JAPANESE_API")
    elif route in ("502","503","504") or direct_route in ("502","503","504"):
        emit("LIKELY_CAUSE","SHARED_API_OR_UPSTREAM_UNHEALTHY")
    elif route=="401" and direct_route=="401":
        if socket_health()!="200":
            emit("LIKELY_CAUSE","PRIVATE_NAS_GATEWAY_OFFLINE")
        elif http(WINDOWS_BRIDGE)!="200":
            emit("LIKELY_CAUSE","NAS_CANNOT_REACH_WINDOWS_BRIDGE_AT_192_168_1_13")
        elif http("http://127.0.0.1:18015/healthz")!="200":
            emit("LIKELY_CAUSE","TRANSLATOR_STANDBY_DOWN")
        else:
            emit("LIKELY_CAUSE","CORE_PATH_HEALTHY_CHECK_SIGNIN_OR_MODEL_INFERENCE")
    elif route=="UNREACHABLE":
        emit("LIKELY_CAUSE","NAS_HTTPS_8443_UNREACHABLE_FROM_NAS")
    else:
        emit("LIKELY_CAUSE","SEE_STATUS_CODES")
    emit("CHANGES_MADE","NONE")
    emit("CHECK_COMPLETE","YES")

if __name__=="__main__":
    try: main()
    except Exception as e:
        emit("CHECK_COMPLETE","ERROR")
        emit("ERROR_CLASS",type(e).__name__)
        sys.exit(1)
