#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys, time, urllib.parse
from pathlib import Path

PACK_DIR = Path(os.environ.get("PACK_DIR", "voicevox-pack"))
PACK_INDEX = PACK_DIR / "voicevox-index.json"
INDEX_OUT = Path(os.environ.get("INDEX_OUT", "voicevox-release-index.json"))
REPO = os.environ.get("GITHUB_REPOSITORY", "kanuli/japanese-vocab-game")
NAMESPACE = os.environ.get("RELEASE_NAMESPACE", "voicevox-v1")
MAX_ASSETS = int(os.environ.get("RELEASE_MAX_ASSETS", "800"))
UPLOAD_BATCH = max(1, int(os.environ.get("RELEASE_UPLOAD_BATCH", "10")))
UPLOAD_RETRIES = max(1, int(os.environ.get("RELEASE_UPLOAD_RETRIES", "6")))
RETRY_BASE_SECONDS = max(1, int(os.environ.get("RELEASE_RETRY_BASE_SECONDS", "3")))
REPLACE_LEVELS = os.environ.get("REPLACE_LEVELS", "0").lower() in {"1","true","yes"}
HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO","kanuli1983/japanese-listening-voicevox-backup").strip()

def run(*args: str, check: bool=True, timeout: int|None=None):
    return subprocess.run(args, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)

def detail(exc, timeout: int) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        return (exc.stderr or exc.stdout or "").strip()
    return f"timed out after {timeout}s"

def is_rate_limit(text: str) -> bool:
    t=text.lower()
    return "rate limit exceeded" in t or "api rate limit" in t

def run_retry(*args: str, attempts: int=UPLOAD_RETRIES, timeout: int=300):
    last=None
    for attempt in range(1, attempts+1):
        try:
            r=run(*args, timeout=timeout)
            if attempt>1:
                print(f"Recovered on retry {attempt}/{attempts}: {' '.join(args[:4])}")
            return r
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            last=exc
            d=detail(exc, timeout)
            print(f"Command failed ({attempt}/{attempts}): {' '.join(args)}"+(f"\n{d}" if d else ""), file=sys.stderr)
            if is_rate_limit(d):
                print("GitHub installation API rate limit reached. Stopping immediately; resume the saved pack later without regenerating audio.", file=sys.stderr)
                raise
            if attempt<attempts:
                delay=min(RETRY_BASE_SECONDS*(2**(attempt-1)),45)
                print(f"Retrying in {delay}s...", file=sys.stderr)
                time.sleep(delay)
    raise last

def quote_path(path: str) -> str:
    return "/".join(urllib.parse.quote(part, safe="") for part in path.split("/") if part)

def hf_public_url(relative_path: str) -> str:
    if not HF_DATASET_REPO: return ""
    return f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/{quote_path(relative_path)}"

def release_assets(tag: str) -> dict[str,int]:
    r=run_retry("gh","release","view",tag,"--repo",REPO,"--json","assets",attempts=3,timeout=120)
    payload=json.loads(r.stdout or "{}")
    return {str(a.get("name","")): int(a.get("size") or 0) for a in (payload.get("assets") or []) if a.get("name")}

def ensure_release(tag: str, level: str, chunk: int):
    found=run("gh","release","view",tag,"--repo",REPO,check=False,timeout=120)
    if found.returncode==0: return
    d=(found.stderr or found.stdout or "").strip()
    if is_rate_limit(d):
        raise subprocess.CalledProcessError(found.returncode, found.args, found.stdout, found.stderr)
    run_retry("gh","release","create",tag,"--repo",REPO,"--title",f"VOICEVOX {level} audio {chunk:03d}","--notes","Pre-generated VOICEVOX audio for the Japanese Listening Game.",attempts=5,timeout=180)

def delete_remote_asset(tag: str, name: str):
    run_retry("gh","release","delete-asset",tag,name,"--repo",REPO,"-y",attempts=3,timeout=120)

def upload_batch(tag: str, paths: list[Path], known: dict[str,int]):
    reused=replaced=0
    todo=[]
    for p in paths:
        local=p.stat().st_size
        remote=known.get(p.name)
        if remote==local and remote>0:
            reused+=1
            continue
        if remote is not None:
            delete_remote_asset(tag,p.name)
            known.pop(p.name,None)
            replaced+=1
        todo.append(p)
    if todo:
        run_retry("gh","release","upload",tag,"--repo",REPO,*map(str,todo),attempts=UPLOAD_RETRIES,timeout=600)
        for p in todo:
            known[p.name]=p.stat().st_size
    return len(todo), replaced, reused

def write_checkpoint(stable: dict):
    stable["indexed"]=len(stable.get("items") or {})
    INDEX_OUT.write_text(json.dumps(stable,ensure_ascii=False,indent=2),encoding="utf-8")

def main():
    if not PACK_INDEX.is_file(): raise SystemExit(f"Missing {PACK_INDEX}")
    pack=json.loads(PACK_INDEX.read_text(encoding="utf-8"))
    source=pack.get("items") or {}
    if not source: raise SystemExit("Generated pack has no items")
    if not 1<=MAX_ASSETS<=950: raise SystemExit("RELEASE_MAX_ASSETS must be between 1 and 950")
    stable={"version":2,"storage":"github-releases+hf-backup","items":{}}
    if INDEX_OUT.is_file():
        try:
            old=json.loads(INDEX_OUT.read_text(encoding="utf-8"))
            if isinstance(old,dict) and isinstance(old.get("items"),dict): stable=old
        except Exception: pass
    stable.update({"version":2,"storage":"github-releases+hf-backup","primaryStorage":"github-releases","backupStorage":"huggingface-dataset" if HF_DATASET_REPO else "","huggingFaceDataset":HF_DATASET_REPO})
    stable.setdefault("items",{})
    levels={str(r.get("level","")).upper() for r in source.values() if r.get("level")}
    if REPLACE_LEVELS:
        stable["items"]={qid:r for qid,r in stable["items"].items() if str(r.get("level","")).upper() not in levels}
    by={}
    for qid,rec in source.items():
        level=str(rec.get("level","")).upper()
        if not level: raise SystemExit(f"Missing level for {qid}")
        by.setdefault(level,[]).append((qid,rec))
    uploaded=replaced=reused=0
    used=set()
    for level in sorted(by):
        rows=by[level]
        for offset in range(0,len(rows),MAX_ASSETS):
            chunk=offset//MAX_ASSETS+1
            chunk_rows=rows[offset:offset+MAX_ASSETS]
            tag=f"{NAMESPACE}-{level.lower()}-{chunk:03d}"
            ensure_release(tag,level,chunk); used.add(tag)
            known=release_assets(tag)
            expected={}
            pending=[]
            for qid,rec in chunk_rows:
                rel=str(rec["path"]); p=PACK_DIR/rel
                if not p.is_file(): raise SystemExit(f"Missing audio: {p}")
                expected[p.name]=p.stat().st_size
                primary=f"https://github.com/{REPO}/releases/download/{urllib.parse.quote(tag)}/{urllib.parse.quote(p.name)}"
                backup=hf_public_url(rel)
                stable["items"][qid]={"url":primary,"urls":[primary]+([backup] if backup else []),"backupUrl":backup,"path":rel,"speaker":rec.get("speaker",""),"style":rec.get("style",""),"styleId":rec.get("styleId"),"credit":rec.get("credit",""),"text":rec.get("text",""),"grammar":rec.get("grammar",""),"level":level,"release":tag,"asset":p.name}
                pending.append(p)
                if len(pending)>=UPLOAD_BATCH:
                    a,b,c=upload_batch(tag,pending,known); uploaded+=a; replaced+=b; reused+=c
                    print(f"{tag}: uploaded {uploaded}, replaced {replaced}, reused {reused} total")
                    pending=[]; write_checkpoint(stable)
            if pending:
                a,b,c=upload_batch(tag,pending,known); uploaded+=a; replaced+=b; reused+=c
                print(f"{tag}: uploaded {uploaded}, replaced {replaced}, reused {reused} total")
                write_checkpoint(stable)
            final=release_assets(tag)
            bad=[n for n,s in expected.items() if final.get(n)!=s]
            if bad: raise RuntimeError(f"{tag}: {len(bad)} asset(s) missing or wrong size: {', '.join(bad[:10])}")
            print(f"Verified {tag}: {len(expected)} expected assets are present ({len(final)} total assets in Release)")
    stable["releaseNamespace"]=NAMESPACE
    stable["releases"]=sorted({r.get("release") for r in stable["items"].values() if r.get("release")})
    stable["voiceVariantCount"]=pack.get("voiceVariantCount")
    stable["speakerCount"]=pack.get("speakerCount")
    stable["publisher"]={"uploadBatch":UPLOAD_BATCH,"uploadRetries":UPLOAD_RETRIES,"resumable":True,"avoidClobberForNewAssets":True,"failFastOnRateLimit":True}
    write_checkpoint(stable)
    print(f"Published {uploaded} new assets; replaced {replaced}; reused {reused}; verified {len(used)} release(s)")
    return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        if exc.stdout: print(exc.stdout,file=sys.stderr)
        if exc.stderr: print(exc.stderr,file=sys.stderr)
        raise SystemExit(exc.returncode or 1)
    except subprocess.TimeoutExpired as exc:
        print(f"Command timed out: {exc.cmd}",file=sys.stderr)
        raise SystemExit(124)
