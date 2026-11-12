#!/usr/bin/env python3
"""Step 9AR: improved read-only classification for the prior 8443 502 incident.

Only inspects historical nginx error/access log lines around 2026-11-12
20:08-20:14 HKT (also UTC 12:08-12:14). Prints counts/categories only.
Does not print raw logs, client identifiers, translation texts or secrets.
No live containers start/restart, no Nginx edits, no database read.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

DOCKER="/usr/local/bin/docker"
HOME=Path.home()
ROOT=Path("/volume2/docker/japanese-api")
BACKUP=HOME/"japanese-api-rollbacks"/"preplamo-20261112_130956"
PUBLIC="https://kanu-rustdesk.synology.me:8443/healthz"
RESOLVE="kanu-rustdesk.synology.me:8443:127.0.0.1"

def emit(key,value):
    print("%s=%s"%(key,value),flush=True)

def exec_command(args,timeout=25):
    r=subprocess.run(args,stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        text=True,errors="replace",timeout=timeout,check=False)
    return r

def docker(*args):
    r=exec_command(["sudo","-n",DOCKER]+list(args))
    if r.returncode:
        raise RuntimeError("DOCKER_READ_FAILED")
    return r.stdout.strip()

def public_health():
    r=exec_command(["curl","-ksS","--connect-timeout","5",
            "--max-time","12","-o","/dev/null","-w","%{http_code}",
            "--resolve",RESOLVE,PUBLIC],timeout=16)
    return r.stdout.strip() if r.returncode==0 else "UNAVAILABLE"

def incident(line):
    # Accept Synology nginx local HKT or UTC and access-log date styles.
    return bool(re.search(
       r"(?:2026[/\-]11[/\-]12[ T](?:20|12):(?:08|09|10|11|12|13|14):"
       r"|12/Nov/2026:(?:20|12):(?:08|09|10|11|12|13|14):)",line))

def error_type(line):
    t=line.lower()
    # Check specific errors BEFORE generic upstream events.
    patterns=[
       ("CONNECT_REFUSED", ("connection refused", "connect() failed", "(111:")),
       ("CONNECTION_RESET", ("connection reset by peer", "recv() failed", "(104:")),
       ("UPSTREAM_TIMEOUT", ("upstream timed out", "timed out (110:", "timeout while")),
       ("PREMATURE_CLOSE", ("upstream prematurely closed", "prematurely closed connection")),
       ("NO_LIVE_UPSTREAMS", ("no live upstreams", "upstream server temporarily disabled")),
       ("UPSTREAM_INVALID_HEADER", ("upstream sent invalid header", "invalid header while")),
       ("DNS_OR_RESOLVER", ("host not found in upstream", "no resolver defined", "could not be resolved")),
       ("PERMISSION_DENIED", ("permission denied", "(13:")),
       ("NO_SUCH_FILE", ("no such file or directory", "(2:")),
       ("ADDRESS_IN_USE", ("address already in use", "(98:", "bind()")),
       ("SSL_HANDSHAKE", ("ssl_do_handshake", "ssl handshake")),
       ("NO_ROUTE_TO_HOST", ("no route to host", "(113:")),
       ("UPSTREAM_GENERIC", ("upstream:", "while connecting to upstream", "while reading response header from upstream")),
       ("HTTP_502", ('" 502 ', " 502 ")),
       ("HTTP_503", ('" 503 ', " 503 ")),
    ]
    for category, phrases in patterns:
        if any(p in t for p in phrases): return category
    if "error" in t or "critical" in t or "warn" in t: return "OTHER_NGINX_ERROR"
    return "OTHER"


def safe_features(line):
    # The only emitted values are short enum labels and numeric errno/port.
    t=line.lower()
    severity=re.search(r"\[(emerg|alert|crit|error|warn|notice|info|debug)\]",t)
    code=re.search(r"\(([0-9]{1,4}):",line)
    indicators={
        "HAS_UPSTREAM":"upstream" in t,
        "HAS_CONNECT":"connect" in t,
        "HAS_READ":"read" in t,
        "HAS_WRITE":"write" in t or "send" in t,
        "HAS_TIMEOUT":"timed out" in t or "timeout" in t,
        "HAS_REFUSED":"refused" in t,
        "HAS_RESET":"reset" in t,
        "HAS_SSL":"ssl" in t,
        "HAS_HTTP_502":bool(re.search(r'(?<!\d)502(?!\d)',line)),
        "MENTIONS_8015":"8015" in t,
        "MENTIONS_8443":"8443" in t,
    }
    # Allow only approved enum feature keys, no raw lines or free-form data.
    feature=",".join(k for k,v in indicators.items() if v) or "NONE"
    return {
        "severity":(severity.group(1).upper() if severity else "UNKNOWN"),
        "errno":(code.group(1) if code else "NONE"),
        "flags":feature,
    }

def tail_file(path):
    # Read only existing regular files from fixed log directory.
    r=exec_command(["sudo","-n","tail","-n","25000",path],timeout=20)
    if r.returncode:
        return None
    return r.stdout.splitlines()

def main():
    emit("PHASE","9AR_TRANSLATOR_502_LOG_SIGNATURE_READONLY")
    for p in (ROOT/"app"/"main.py", BACKUP/"api-source.tar.gz",
              BACKUP/"image-id.txt"):
        if not p.is_file() or p.is_symlink():
            raise RuntimeError("SOURCE_OR_BACKUP_MISSING_STOP")
    with tarfile.open(str(BACKUP/"api-source.tar.gz"),"r:gz") as t:
        f=t.extractfile("app/main.py")
        if not f:
            raise RuntimeError("BACKUP_MAIN_MISSING")
        if hashlib.sha256(f.read()).digest()!=hashlib.sha256(
                (ROOT/"app"/"main.py").read_bytes()).digest():
            raise RuntimeError("PRODUCTION_SOURCE_CHANGED_STOP")
    emit("ORIGINAL_SOURCE_MATCH","PASS")
    r=subprocess.run(["sudo","-v"],check=False)
    if r.returncode: raise RuntimeError("SUDO_AUTH_FAILED")
    original=(BACKUP/"image-id.txt").read_text().strip()
    if docker("inspect","--format","{{.Image}}","japanese-api")!=original:
        raise RuntimeError("RESTORED_IMAGE_NOT_ORIGINAL_STOP")
    if docker("inspect","--format","{{.State.Running}}","japanese-api")!="true":
        raise RuntimeError("PRODUCTION_NOT_RUNNING_STOP")
    before=public_health()
    emit("PUBLIC_8443_BEFORE",before)
    if before!="200": raise RuntimeError("PRODUCTION_8443_UNHEALTHY_STOP")
    paths=[]
    # Only existing files under the system Nginx log directory; never
    # recursively crawl private directories or echo raw path contents.
    for dirname in (Path("/var/log/nginx"),Path("/var/log")):
        if not dirname.is_dir():
            continue
        try:
            for p in dirname.iterdir():
                name=p.name.lower()
                if (p.is_file() and not p.is_symlink() and
                    (("nginx" in str(dirname).lower() and
                      ("error" in name or "access" in name)) or
                     ("nginx" in name and ("error" in name or "access" in name)))):
                    paths.append(str(p))
        except PermissionError:
            continue
    # Synology often stores nginx logs under /var/log/nginx where even
    # directory enumeration is privileged. Add a small set of fixed candidates.
    paths += [
        "/var/log/nginx/error.log",
        "/var/log/nginx/access.log",
        "/var/log/nginx/error.log.1",
        "/var/log/nginx/access.log.1",
        "/var/log/nginx/error_log",
        "/var/log/nginx/access_log",
        "/var/log/nginx_error.log",
        "/var/log/nginx_access.log",
    ]
    # Preserve order, bound number of files. No raw error-log excerpts.
    paths=list(dict.fromkeys(paths))[:18]
    count=collections.Counter()
    evidence=collections.Counter()
    total=0
    matched_files=0
    accessible_files=0
    for p in paths:
        lines=tail_file(p)
        if lines is None:
            continue
        accessible_files+=1
        found=False
        for line in lines:
            if not incident(line):
                continue
            found=True
            total+=1
            klass=error_type(line)
            count[klass]+=1
            feature=safe_features(line)
            signature=(klass,feature["severity"],feature["errno"],feature["flags"])
            evidence[signature]+=1
        if found: matched_files+=1
    emit("NGINX_LOG_FILES_READABLE",accessible_files)
    emit("NGINX_LOG_FILES_WITH_INCIDENT_TIMESTAMP",matched_files)
    emit("INCIDENT_TIMESTAMP_LINES",total)
    for category,num in sorted(count.items()):
        emit("INCIDENT_CATEGORY_"+category,num)
    emit("ERROR_SIGNATURE_GROUPS",len(evidence))
    for i, ((kind,severity,errno,flags),amount) in enumerate(
            sorted(evidence.items(),key=lambda x:(-x[1],x[0]))[:12]):
        emit("SIGNATURE_%02d_COUNT"%i,amount)
        emit("SIGNATURE_%02d_CLASS"%i,kind)
        emit("SIGNATURE_%02d_SEVERITY"%i,severity)
        emit("SIGNATURE_%02d_ERRNO"%i,errno)
        emit("SIGNATURE_%02d_FLAGS"%i,flags)
    relevant=sum(amount for (klass,sev,eno,flags),amount in evidence.items()
                 if "HAS_UPSTREAM" in flags or "MENTIONS_8015" in flags)
    emit("INCIDENT_UPSTREAM_OR_8015_RELEVANT_LINES",relevant)
    emit("HISTORICAL_ROOT_CAUSE",
         "UNCONFIRMED_REVIEW_STRUCTURED_SIGNATURES")
    after=public_health()
    emit("PUBLIC_8443_AFTER",after)
    if after!="200" or docker("inspect","--format","{{.Image}}","japanese-api")!=original:
        raise RuntimeError("PRODUCTION_HEALTH_OR_IMAGE_CHANGED_STOP")
    emit("PRODUCTION_IMAGE_UNCHANGED","PASS")
    emit("CONTAINERS_CREATED_OR_RESTARTED","NO")
    emit("SQLITE_OPENED_OR_COPIED","NO")
    emit("NGINX_CONFIG_MODIFIED","NO")
    emit("STEP_9AR","PASS")

if __name__=="__main__":
    try: main()
    except Exception as ex:
        emit("STEP_9AR","FAIL")
        emit("STOP_REASON",str(ex)[:180])
        sys.exit(1)
