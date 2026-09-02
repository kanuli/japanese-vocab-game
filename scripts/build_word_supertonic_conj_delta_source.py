#!/usr/bin/env python3
"""Build F3 conjugation-audio source: unique readings not already hosted."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORDS = Path(os.environ.get("CONJ_WORDS_JSON", "word-supertonic3-conj-words.json"))
OUT = Path(os.environ.get("OUT", "word-supertonic3-conj-source.json"))
PLAN = Path(os.environ.get("PLAN_OUT", "word-supertonic3-conj-plan.json"))
ENUM = ROOT / "scripts" / "enumerate_conjugation_readings.js"
MAX_NEW = int(os.environ.get("CONJ_MAX_NEW", "8000"))
SHARDS = int(os.environ.get("SHARD_COUNT", "0"))
CATALOGS = [
    Path(os.environ.get("BASE_CATALOG", "word-supertonic3-catalog.json")),
    Path(os.environ.get("DELTA1_CATALOG", "word-supertonic3-delta-catalog.json")),
    Path(os.environ.get("RUNTIME_CATALOG", "word-supertonic3-runtime-delta-catalog.json")),
    Path(os.environ.get("VOICEVOX_CATALOG", "word-voicevox-catalog.json")),
    Path(os.environ.get("AIVIS_CATALOG", "word-aivis-catalog.json")),
]


def nfkc_hira(s: str) -> str:
    s = unicodedata.normalize("NFKC", str(s or ""))
    out = []
    for ch in s:
        o = ord(ch)
        if 0x30A1 <= o <= 0x30F6:
            out.append(chr(o - 96))
        elif not ch.isspace():
            out.append(ch)
    return "".join(out)


def hosted_readings() -> set[str]:
    found: set[str] = set()
    loaded = []
    for path in CATALOGS:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        words = data.get("words") if isinstance(data, dict) else None
        if not isinstance(words, dict):
            continue
        loaded.append(str(path))
        for key in words:
            reading = str(key).split("|", 1)[0]
            r = nfkc_hira(reading)
            if r:
                found.add(r)
    if not found:
        raise SystemExit("No hosted catalogs found for reading skip-list")
    print("Hosted catalogs:", ", ".join(loaded), "readings", len(found), flush=True)
    return found


def enumerate_readings() -> dict:
    if not WORDS.is_file():
        raise SystemExit(f"Missing conjugable-word JSON: {WORDS}")
    tmp = Path(os.environ.get("ENUM_TMP", "word-supertonic3-conj-enum.json"))
    subprocess.check_call(["node", str(ENUM), str(WORDS), str(tmp)])
    return json.loads(tmp.read_text(encoding="utf-8"))


hosted = hosted_readings()
enum = enumerate_readings()
items_in = enum.get("items") or []
seen: set[str] = set()
already = 0
unique = []
for row in items_in:
    reading = nfkc_hira(row.get("reading") or "")
    if not reading or reading in seen:
        continue
    seen.add(reading)
    if reading in hosted:
        already += 1
        continue
    unique.append({"reading": reading, "written": str(row.get("written") or reading)})

unique.sort(key=lambda x: x["reading"])
capped = False
if MAX_NEW > 0 and len(unique) > MAX_NEW:
    unique = unique[:MAX_NEW]
    capped = True

if SHARDS < 1:
    SHARDS = 1 if not unique else min(8, max(1, (len(unique) + 499) // 500))

items = []
words = {}
counts = [0] * max(SHARDS, 1)
ids = set()
for i, row in enumerate(unique):
    key = f"{row['reading']}|{row['written']}"
    wid = hashlib.sha256(("conj-supertonic3-v1\0" + row["reading"]).encode("utf-8")).hexdigest()[:16]
    if wid in ids:
        raise SystemExit(f"Recording ID collision: {wid}")
    ids.add(wid)
    shard = i % SHARDS
    counts[shard] += 1
    items.append({"id": wid, "key": key, "reading": row["reading"], "written": row["written"], "shard": shard})
    words[key] = [wid, shard]

if unique and any(n == 0 for n in counts):
    raise SystemExit(f"Unexpected empty conj shard: {counts}")

out = {
    "version": 1,
    "status": "catalog",
    "engine": "supertonic-3-conj-delta-source",
    "language": "ja",
    "coverageRule": "unique NFKC kana readings of basic+extended conjugations missing from hosted catalogs",
    "verbCount": int(enum.get("verbCount") or 0),
    "uniqueReadingCount": int(enum.get("uniqueReadingCount") or 0),
    "alreadyHostedReadingCount": already,
    "newReadingCount": len(items),
    "capped": capped,
    "cap": MAX_NEW,
    "wordCount": len(items),
    "shardCount": SHARDS if unique else 0,
    "shardCounts": counts if unique else [],
    "voices": ["F3"],
    "items": items,
    "words": words,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
plan = {k: out[k] for k in (
    "version", "status", "engine", "coverageRule", "verbCount", "uniqueReadingCount",
    "alreadyHostedReadingCount", "newReadingCount", "capped", "cap", "wordCount",
    "shardCount", "shardCounts", "voices",
)}
plan["hostedAudioStatus"] = "pending-actions"
plan["releaseTag"] = "word-supertonic3-conj-v1"
plan["hfDir"] = "word/supertonic3/conj-v1"
plan["note"] = "Clips appear after generate-word-supertonic3-conj-delta.yml publishes GitHub Release word-supertonic3-conj-v1. Do not mark hosted conjugation audio PASS until the ready catalog exists."
PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(plan, ensure_ascii=False, indent=2))
