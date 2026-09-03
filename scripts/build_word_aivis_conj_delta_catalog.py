#!/usr/bin/env python3
from __future__ import annotations
import json, os
from pathlib import Path

CAT = Path(os.environ.get("CATALOG", "word-aivis-conj-source.json"))
MODEL = Path(os.environ.get("MODEL", "aivis-model.json"))
M = Path(os.environ.get("MANIFEST_DIR", "word-aivis-conj-manifests"))
OUT = Path(os.environ.get("OUT", "word-aivis-conj-catalog.json"))
REPO = os.environ.get("GITHUB_REPO", "kanuli/japanese-vocab-game")
HF = os.environ.get("HF_DATASET_REPO", "kanuli1983/japanese-listening-voicevox-backup")
TAG = os.environ.get("RELEASE_TAG", "word-aivis-conj-v1")
HF_DIR = os.environ.get("HF_DIR", "word/aivis/conj-v1")

d = json.loads(CAT.read_text(encoding="utf-8"))
model = json.loads(MODEL.read_text(encoding="utf-8"))
words = d.get("words") or {}
items = d.get("items") or []
wc = int(d.get("wordCount", 0))
sc = int(d.get("shardCount", 0))
if d.get("status") != "catalog" or wc < 1 or len(items) != wc:
    raise SystemExit("bad aivis conj source catalog")
voices = {}
for st in model["styles"]:
    k = st["key"]
    bundles = {}
    seen = set()
    for shard in range(sc):
        p = M / f"{k}-shard{shard}.json"
        if not p.is_file():
            raise SystemExit(f"Missing {p}")
        m = json.loads(p.read_text(encoding="utf-8"))
        expected = {x["id"] for x in items if int(x["shard"]) == shard}
        if set(m.get("members") or {}) != expected:
            raise SystemExit(f"{k} shard {shard} coverage mismatch")
        if m.get("licenseSha256") and model.get("licenseSha256") and m.get("licenseSha256") != model["licenseSha256"]:
            raise SystemExit("Aivis license changed between shards")
        asset = m.get("asset") or f"{k}-shard{shard}.tar"
        bundles[str(shard)] = {
            "githubUrl": f"https://github.com/{REPO}/releases/download/{TAG}/{asset}",
            "hfUrl": f"https://huggingface.co/datasets/{HF}/resolve/main/{HF_DIR}/{asset}?download=true",
            "members": m["members"],
        }
        seen |= expected
    if len(seen) != wc:
        raise SystemExit(f"{k}: expected {wc} IDs, got {len(seen)}")
    idx = {
        "version": 1,
        "engine": "aivisspeech-conj-delta",
        "voice": k,
        "speaker": st.get("speaker"),
        "style": st.get("style"),
        "styleId": st.get("styleId"),
        "displayName": f"{st.get('speaker')}｜{st.get('style')}",
        "wordCount": wc,
        "shardCount": sc,
        "bundles": bundles,
    }
    ip = Path(f"word-aivis-conj-{k}-index.json")
    ip.write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    voices[k] = {
        "speaker": st.get("speaker"),
        "style": st.get("style"),
        "displayName": idx["displayName"],
        "indexUrl": f"./{ip.name}?v=1",
        "indexGithubUrl": f"https://github.com/{REPO}/releases/download/{TAG}/{ip.name}",
    }
out = {
    "version": 1,
    "status": "ready",
    "engine": "aivisspeech-conj-delta",
    "storage": "github-releases+hf-range-bundles",
    "coverageRule": d.get("coverageRule"),
    "verbCount": int(d.get("verbCount", 0)),
    "uniqueReadingCount": int(d.get("uniqueReadingCount", 0)),
    "alreadyHostedReadingCount": int(d.get("alreadyHostedReadingCount", 0)),
    "wordCount": wc,
    "voiceCount": len(voices),
    "recordingCount": wc * len(voices),
    "shardCount": sc,
    "words": words,
    "voices": voices,
    "releaseTag": TAG,
}
if not 1 <= out["voiceCount"] <= 4:
    raise SystemExit("Unexpected Aivis conj voice count")
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("Aivis conj:", out["recordingCount"], "recordings /", out["voiceCount"], "styles")
