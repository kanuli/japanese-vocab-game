#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path

CAT=Path(os.environ.get("CATALOG","word-supertonic3-conj-source.json"))
MANIFESTS=Path(os.environ.get("MANIFEST_DIR","word-supertonic-conj-manifests"))
OUT=Path(os.environ.get("OUT","word-supertonic3-conj-catalog.json"))
REPO=os.environ.get("GITHUB_REPO","kanuli/japanese-vocab-game")
HF=os.environ.get("HF_DATASET_REPO","kanuli1983/japanese-listening-voicevox-backup")
TAG=os.environ.get("RELEASE_TAG","word-supertonic3-conj-v1")
HF_DIR=os.environ.get("HF_DIR","word/supertonic3/conj-v1")
VOICES=os.environ.get("VOICES","F3").split(",")
LABELS={"F1":"沉穩低柔女聲（F1）","F2":"明亮活漂女聲（F2）","F3":"專業播音女聲（F3）","F4":"清晰自信女聲（F4）","F5":"溫柔療癒女聲（F5）","M1":"活力自信男聲（M1）","M2":"低沉穩重男聲（M2）","M3":"權威專業男聲（M3）","M4":"柔和親切男聲（M4）","M5":"溫暖舒緩男聲（M5）"}
d=json.loads(CAT.read_text(encoding="utf-8")); words=d.get("words") or {}; items=d.get("items") or []
wc=int(d.get("wordCount",0)); sc=int(d.get("shardCount",0))
if d.get("status")!="catalog" or wc<1 or len(items)!=wc or len(words)!=wc:
    raise SystemExit("bad conj delta source catalog")
voices={}
for voice in VOICES:
    voice=voice.strip()
    if not voice:
        continue
    label=LABELS.get(voice, voice)
    bundles={}; seen=set()
    for shard in range(sc):
        p=MANIFESTS/f"{voice}-shard{shard}.json"
        if not p.is_file():
            raise SystemExit(f"Missing {p}")
        m=json.loads(p.read_text(encoding="utf-8"))
        expected={x["id"] for x in items if int(x["shard"])==shard}
        members=m.get("members") or {}
        if set(members)!=expected:
            raise SystemExit(f"{voice} shard {shard} coverage mismatch")
        asset=m.get("asset") or f"{voice}-shard{shard}.tar"
        bundles[str(shard)]={
            "githubUrl":f"https://github.com/{REPO}/releases/download/{TAG}/{asset}",
            "hfUrl":f"https://huggingface.co/datasets/{HF}/resolve/main/{HF_DIR}/{asset}?download=true",
            "members":members,
        }
        seen|=expected
    if len(seen)!=wc:
        raise SystemExit(f"{voice}: expected {wc} IDs, got {len(seen)}")
    idx={"version":1,"engine":"supertonic-3-conj-delta","voice":voice,"label":label,"wordCount":wc,"shardCount":sc,"bundles":bundles}
    ip=Path(f"word-supertonic3-conj-{voice}-index.json")
    ip.write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":"))+"\n", encoding="utf-8")
    voices[voice]={"label":label,"indexUrl":f"./{ip.name}?v=1","indexGithubUrl":f"https://github.com/{REPO}/releases/download/{TAG}/{ip.name}"}
out={
    "version":1,"status":"ready","engine":"supertonic-3-conj-delta",
    "storage":"github-releases+hf-range-bundles",
    "coverageRule":d.get("coverageRule"),
    "verbCount":int(d.get("verbCount",0)),
    "uniqueReadingCount":int(d.get("uniqueReadingCount",0)),
    "alreadyHostedReadingCount":int(d.get("alreadyHostedReadingCount",0)),
    "wordCount":wc,"voiceCount":len(voices),"recordingCount":wc*len(voices),
    "shardCount":sc,"words":words,"voices":voices,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"))+"\n", encoding="utf-8")
print("Conj Supertonic 3 delta:", wc, "readings /", wc*len(voices), "recordings", list(voices))
