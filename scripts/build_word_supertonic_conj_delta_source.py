#!/usr/bin/env python3
"""Build unique-reading conjugation audio source. Uncapped by default.

Reuse already-hosted same-engine readings (lemma + deltas + existing conj).
Deterministic IDs. Does not regenerate existing clips.
"""
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
AUDIT = Path(os.environ.get("AUDIT_OUT", "word-conj-hosted-audit.json"))
ENUM = ROOT / "scripts" / "enumerate_conjugation_readings.js"
MAX_NEW = int(os.environ.get("CONJ_MAX_NEW", "0"))
SHARDS = int(os.environ.get("SHARD_COUNT", "20"))
ID_PREFIX = os.environ.get("ID_PREFIX", "conj-supertonic3-v2")
ENGINE = os.environ.get("ENGINE", "supertonic-3-conj-delta-source")
VOICES = [v.strip() for v in os.environ.get("VOICES", "F1,F2,F3,F4,F5,M1,M2,M3,M4,M5").split(",") if v.strip()]
RELEASE_TAG = os.environ.get("RELEASE_TAG", "word-supertonic3-conj-v2")
HF_DIR = os.environ.get("HF_DIR", "word/supertonic3/conj-v2")
SKIP_RAW = os.environ.get("SKIP_CATALOGS", "")
DEFAULT_SKIP = [
    "word-supertonic3-catalog.json",
    "word-supertonic3-delta-catalog.json",
    "word-supertonic3-runtime-delta-catalog.json",
    "word-supertonic3-conj-catalog.json",
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


def catalog_paths() -> list[Path]:
    if SKIP_RAW.strip():
        return [Path(p.strip()) for p in SKIP_RAW.split(",") if p.strip()]
    extra = os.environ.get("EXTRA_SKIP_CATALOGS", "")
    paths = [Path(p) for p in DEFAULT_SKIP]
    for p in extra.split(","):
        p = p.strip()
        if p:
            paths.append(Path(p))
    return paths


def hosted_readings() -> tuple[set[str], list[str]]:
    found: set[str] = set()
    loaded = []
    for path in catalog_paths():
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
    return found, loaded


def enumerate_readings() -> dict:
    if not WORDS.is_file():
        raise SystemExit(f"Missing conjugable-word JSON: {WORDS}")
    tmp = Path(os.environ.get("ENUM_TMP", "word-supertonic3-conj-enum.json"))
    subprocess.check_call(["node", str(ENUM), str(WORDS), str(tmp)])
    return json.loads(tmp.read_text(encoding="utf-8"))


hosted, loaded_catalogs = hosted_readings()
enum = enumerate_readings()
items_in = enum.get("items") or []
seen: set[str] = set()
already = 0
duplicates = 0
unique = []
for row in items_in:
    reading = nfkc_hira(row.get("reading") or "")
    if not reading:
        continue
    if reading in seen:
        duplicates += 1
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
    SHARDS = 20 if unique else 0
if unique:
    SHARDS = max(1, min(SHARDS, len(unique)))

items = []
words = {}
counts = [0] * max(SHARDS, 1)
ids = set()
for i, row in enumerate(unique):
    key = f"{row['reading']}|{row['written']}"
    wid = hashlib.sha256((ID_PREFIX + "\0" + row["reading"]).encode("utf-8")).hexdigest()[:16]
    if wid in ids:
        raise SystemExit(f"Recording ID collision: {wid}")
    ids.add(wid)
    shard = i % SHARDS
    counts[shard] += 1
    items.append({"id": wid, "key": key, "reading": row["reading"], "written": row["written"], "shard": shard})
    words[key] = [wid, shard]

if unique and any(n == 0 for n in counts):
    raise SystemExit(f"Unexpected empty conj shard: {counts}")

vocab_scanned = 0
if WORDS.is_file():
    raw = json.loads(WORDS.read_text(encoding="utf-8"))
    vocab_scanned = len(raw) if isinstance(raw, list) else len(raw.get("words") or [])

remaining = len(items)
audit = {
    "version": 2,
    "engine": ENGINE,
    "vocabScanned": vocab_scanned,
    "verbsEligible": int(enum.get("verbCount") or 0),
    "formInstances": int(enum.get("formCount") or 0),
    "uniqueReadings": int(enum.get("uniqueReadingCount") or 0),
    "duplicatesRemoved": duplicates,
    "skipped": int(enum.get("skippedCount") or 0),
    "alreadyHostedReadingCount": already,
    "newReadingCount": remaining,
    "success": already,
    "failure": 0,
    "remainingMissing": remaining,
    "missing_unique_readings": remaining,
    "capped": capped,
    "cap": MAX_NEW,
    "shardCount": SHARDS if unique else 0,
    "shardCounts": counts if unique else [],
    "voices": VOICES,
    "skipCatalogs": loaded_catalogs,
    "releaseTag": RELEASE_TAG,
    "hfDir": HF_DIR,
    "idPrefix": ID_PREFIX,
    "note": "Device TTS is fallback only and does not count as hosted PASS. remainingMissing is unique readings still needing clips for this engine.",
}

out = {
    "version": 1,
    "status": "catalog",
    "engine": ENGINE,
    "language": "ja",
    "coverageRule": "unique NFKC kana readings of basic+extended conjugations missing from same-engine hosted catalogs",
    "verbCount": int(enum.get("verbCount") or 0),
    "uniqueReadingCount": int(enum.get("uniqueReadingCount") or 0),
    "alreadyHostedReadingCount": already,
    "newReadingCount": remaining,
    "capped": capped,
    "cap": MAX_NEW,
    "wordCount": len(items),
    "shardCount": SHARDS if unique else 0,
    "shardCounts": counts if unique else [],
    "voices": VOICES,
    "items": items,
    "words": words,
    "releaseTag": RELEASE_TAG,
    "hfDir": HF_DIR,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
plan = {k: out[k] for k in (
    "version", "status", "engine", "coverageRule", "verbCount", "uniqueReadingCount",
    "alreadyHostedReadingCount", "newReadingCount", "capped", "cap", "wordCount",
    "shardCount", "shardCounts", "voices", "releaseTag", "hfDir",
)}
plan["hostedAudioStatus"] = "pending-actions" if remaining else "complete"
plan["note"] = (
    f"Clips appear after generate workflow publishes GitHub Release {RELEASE_TAG}. "
    "Do not mark hosted conjugation audio PASS until the ready catalog exists. Device TTS is not hosted PASS."
)
PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(plan, ensure_ascii=False, indent=2))
print("AUDIT remaining_unique", remaining, "already", already, "unique", audit["uniqueReadings"], flush=True)
