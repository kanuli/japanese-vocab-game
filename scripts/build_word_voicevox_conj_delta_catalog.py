#!/usr/bin/env python3
"""Build VOICEVOX conjugation unique-reading catalog + per-speaker indexes."""
from __future__ import annotations
import json, os
from pathlib import Path

CAT = Path(os.environ.get("CATALOG", "word-voicevox-conj-source.json"))
MANIFESTS = Path(os.environ.get("MANIFEST_DIR", "word-voicevox-conj-manifests"))
OUT = Path(os.environ.get("OUT", "word-voicevox-conj-catalog.json"))
REPO = os.environ.get("GITHUB_REPO", "kanuli/japanese-vocab-game")
HF = os.environ.get("HF_DATASET_REPO", "kanuli1983/japanese-listening-voicevox-backup")
TAG = os.environ.get("RELEASE_TAG", "word-voicevox-conj-v1")
HF_DIR = os.environ.get("HF_DIR", "word/voicevox/conj-v1")
EXPECTED = os.environ.get("SPEAKERS", "").strip()

d = json.loads(CAT.read_text(encoding="utf-8"))
words = d.get("words") or {}
items = d.get("items") or []
wc = int(d.get("wordCount", 0))
sc = int(d.get("shardCount", 0))
if d.get("status") != "catalog" or wc < 1 or len(items) != wc or len(words) != wc:
    raise SystemExit("bad voicevox conj source catalog")

files = sorted(MANIFESTS.glob("*.json"))
by = {}
ident = {}
for p in files:
    m = json.loads(p.read_text(encoding="utf-8"))
    key = str(m.get("speakerKey") or m.get("voice") or "")
    shard = int(m["shard"])
    if not key:
        raise SystemExit(f"manifest missing speakerKey: {p}")
    if shard in by.setdefault(key, {}):
        raise SystemExit(f"duplicate {key}/{shard}")
    by[key][shard] = m
    ident[key] = (str(m.get("speaker") or key), str(m.get("style") or ""), int(m.get("styleId") or 0), str(m.get("credit") or f"VOICEVOX:{m.get('speaker') or key}"))

if EXPECTED:
    want = [s.strip() for s in EXPECTED.split(",") if s.strip()]
    missing = [s for s in want if s not in by]
    if missing:
        raise SystemExit(f"missing speakers {missing}")

speakers = {}
for key in sorted(by):
    if set(by[key]) != set(range(sc)):
        raise SystemExit(f"{key} missing shards {sorted(set(range(sc)) - set(by[key]))}")
    speaker, style, style_id, credit = ident[key]
    bundles = {}
    seen = set()
    for shard in range(sc):
        m = by[key][shard]
        expected = {x["id"] for x in items if int(x["shard"]) == shard}
        members = m.get("members") or {}
        if set(members) != expected:
            raise SystemExit(f"{key} shard {shard} coverage mismatch")
        asset = m.get("asset") or f"{key}-shard{shard}.tar"
        bundles[str(shard)] = {
            "githubUrl": f"https://github.com/{REPO}/releases/download/{TAG}/{asset}",
            "hfUrl": f"https://huggingface.co/datasets/{HF}/resolve/main/{HF_DIR}/{asset}?download=true",
            "members": members,
        }
        seen |= expected
    if len(seen) != wc:
        raise SystemExit(f"{key}: expected {wc} IDs, got {len(seen)}")
    idx = {
        "version": 1,
        "engine": "voicevox-conj-delta",
        "speakerKey": key,
        "speaker": speaker,
        "style": style,
        "styleId": style_id,
        "credit": credit,
        "wordCount": wc,
        "shardCount": sc,
        "bundles": bundles,
    }
    ip = Path(f"word-voicevox-conj-{key}-index.json")
    ip.write_text(json.dumps(idx, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    speakers[key] = {
        "speaker": speaker,
        "style": style,
        "styleId": style_id,
        "credit": credit,
        "indexUrl": f"./{ip.name}?v=1",
        "indexGithubUrl": f"https://github.com/{REPO}/releases/download/{TAG}/{ip.name}",
        "indexHfUrl": f"https://huggingface.co/datasets/{HF}/resolve/main/{HF_DIR}/indexes/{ip.name}",
    }

out = {
    "version": 1,
    "status": "ready",
    "engine": "voicevox-conj-delta",
    "storage": "github-releases+hf-range-bundles",
    "coverageRule": d.get("coverageRule"),
    "verbCount": int(d.get("verbCount", 0)),
    "uniqueReadingCount": int(d.get("uniqueReadingCount", 0)),
    "alreadyHostedReadingCount": int(d.get("alreadyHostedReadingCount", 0)),
    "wordCount": wc,
    "speakerCount": len(speakers),
    "recordingCount": wc * len(speakers),
    "shardCount": sc,
    "words": words,
    "speakers": speakers,
    "releaseTag": TAG,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("VOICEVOX conj:", wc, "readings /", wc * len(speakers), "recordings", list(speakers))
