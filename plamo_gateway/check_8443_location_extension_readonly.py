#!/usr/bin/env python3
"""9AT: READ-ONLY determine if current Synology 8443 server has a safe
server-local include hook for a single PLaMo translation location.

Print only structural Nginx information, never full config, certificates,
tokens, log contents, request data or environment. Do not edit/reload Nginx,
restart Docker or modify Japanese API or any website page.
"""
from pathlib import Path
import hashlib
import re
import subprocess
import sys
import tarfile

ROOT=Path("/volume2/docker/japanese-api")
BACKUP=Path.home()/"japanese-api-rollbacks"/"preplamo-20261112_130956"
DOCKER="/usr/local/bin/docker"

def out(k,v):
    print("%s=%s"%(k,v),flush=True)

def command(args,timeout=25,check=True):
    p=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,text=True,errors="replace",
                     timeout=timeout,check=False)
    if check and p.returncode:
        raise RuntimeError("READ_FAILED_"+Path(args[0]).name)
    return p

def verified():
    paths=[ROOT/"app/main.py",BACKUP/"api-source.tar.gz",BACKUP/"image-id.txt"]
    if any(not p.is_file() or p.is_symlink() for p in paths):
        raise RuntimeError("BACKUP_OR_SOURCE_MISSING")
    with tarfile.open(str(paths[1]),"r:gz") as t:
        f=t.extractfile("app/main.py")
        if f is None or hashlib.sha256(f.read()).digest() != hashlib.sha256(
                paths[0].read_bytes()).digest():
            raise RuntimeError("PRODUCTION_SOURCE_CHANGED")
    command(["sudo","-v"])
    p=command(["sudo","-n",DOCKER,"inspect","--format","{{.Image}}","japanese-api"])
    if p.stdout.strip()!=paths[2].read_text().strip():
        raise RuntimeError("PRODUCTION_IMAGE_NOT_ORIGINAL")
    out("PRODUCTION_IMAGE_ORIGINAL","PASS")
    p=command(["curl","-ksS","--connect-timeout","4","--max-time","10",
               "-o","/dev/null","-w","%{http_code}",
               "--resolve","kanu-rustdesk.synology.me:8443:127.0.0.1",
               "https://kanu-rustdesk.synology.me:8443/healthz"],check=False)
    if p.returncode or p.stdout.strip()!="200":
        raise RuntimeError("PUBLIC_8443_NOT_HEALTHY")
    out("PUBLIC_8443_HEALTH",200)
    p=command(["curl","-sS","--connect-timeout","3","--max-time","8",
               "-o","/dev/null","-w","%{http_code}",
               "http://127.0.0.1:18015/healthz"],check=False)
    if p.returncode or p.stdout.strip()!="200":
        raise RuntimeError("PLAMO_STANDBY_NOT_HEALTHY")
    out("PLAMO_STANDBY_HEALTH",200)

def extract_servers(text):
    # Parse effective Nginx text without echoing any raw directives.
    # Requires 'server {' at beginning of a line; maintain matching braces.
    servers=[]
    mlist=list(re.finditer(r'(?m)^[ \t]*server[ \t]*\{',text))
    for match in mlist:
        depth=1
        start=match.end()
        pos=start
        while pos<len(text) and depth:
            c=text[pos]
            if c=='{': depth+=1
            elif c=='}': depth-=1
            pos+=1
        if depth==0:
            body=text[start:pos-1]
            if re.search(r'(?m)^\s*listen\s+[^;]*\b8443\b[^;]*;',body):
                servers.append(body)
    return servers

def server_details(body):
    depth=1
    positions=[]
    for line in body.splitlines():
        stripped=re.sub(r'#.*$','',line).strip()
        if depth==1 and re.match(r'^include\s+',stripped):
            raw=re.search(r'^include\s+([^;]+);',stripped)
            if raw:
                path=raw.group(1).strip().strip('"').strip("'")
                if path.startswith('/'):
                    positions.append(path)
        depth+=stripped.count('{')-stripped.count('}')
    locations=re.findall(r'(?m)^[ \t]*location[ \t]+([^\n{]+)\{',body)
    out("SERVER_8443_LOCATION_COUNT",len(locations))
    out("TRANSLATION_EXACT_LOCATION_ALREADY_PRESENT",
        "YES" if any("/api/v1/translate/plamo" in x for x in locations) else "NO")
    out("SERVER_8443_DIRECT_INCLUDE_COUNT",len(positions))
    for i,path in enumerate(positions[:10]):
        # Static path/extension only: no config contents or credentials.
        out("SERVER_8443_INCLUDE_%02d"%i,path[:170])
    out("SERVER_HAS_EXTENSION_HOOK","YES" if positions else "NO")
    if not positions:
        out("PATH_ONLY_ROUTE_SUPPORT","NOT_CONFIRMED_NO_SERVER_INCLUDE")
    else:
        out("PATH_ONLY_ROUTE_SUPPORT","INSPECT_INCLUDE_CONTEXT_REQUIRED")

def main():
    out("PHASE","9AT_TRANSLATOR_ONLY_8443_LOCATION_HOOK_READONLY")
    verified()
    # Try active Nginx first; Synology DSM often needs nginx.conf.run.
    bins=("/usr/syno/bin/nginx","/usr/syno/sbin/nginx","/usr/sbin/nginx")
    content=None
    for binary in bins:
        if not Path(binary).exists(): continue
        for cfg in (None,"/etc/nginx/nginx.conf.run"):
            a=["sudo","-n",binary,"-T"]
            if cfg:a.extend(["-c",cfg])
            p=command(a,timeout=25,check=False)
            if p.returncode==0 and len(p.stdout)>100:
                content=p.stdout
                break
        if content:break
    if content is None:
        out("NGINX_EFFECTIVE_CONFIG","UNAVAILABLE")
        raise RuntimeError("NGINX_EFFECTIVE_READ_UNAVAILABLE")
    servers=extract_servers(content)
    out("NGINX_EFFECTIVE_READ","PASS")
    out("SERVER_8443_MATCHES",len(servers))
    if len(servers)!=1:
        raise RuntimeError("AMBIGUOUS_8443_SERVER_STOP")
    server_details(servers[0])
    # Verify no changes to production, once again.
    if command(["sudo","-n",DOCKER,"inspect","--format","{{.Image}}",
                "japanese-api"]).stdout.strip()!=(BACKUP/"image-id.txt").read_text().strip():
        raise RuntimeError("PRODUCTION_IMAGE_CHANGED")
    out("PRODUCTION_API_RESTARTED","NO")
    out("NGINX_RELOADED_OR_MODIFIED","NO")
    out("PRODUCTION_SQLITE_ACCESSED","NO")
    out("STEP_9AT","PASS")

if __name__=="__main__":
    try:
        main()
    except Exception as exc:
        out("STEP_9AT","FAIL")
        out("STOP_REASON",str(exc)[:180])
        sys.exit(1)
