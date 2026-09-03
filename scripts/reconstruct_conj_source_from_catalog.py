#!/usr/bin/env python3
"""Rebuild a generate-able source JSON from a ready conj catalog's words map."""
from __future__ import annotations
import json, os
from pathlib import Path

CAT = Path(os.environ.get("CATALOG", "word-supertonic3-conj-catalog.json"))
OUT = Path(os.environ.get("OUT", "word-supertonic3-conj-v1-source.json"))
VOICES = [v.strip() for v in os.environ.get("VOICES", "F1,F2,F4,F5,M1,M2,M3,M4,M5").split(",") if v.strip()]
d = json.loads(CAT.read_text(encoding="utf-8"))
words = d.get("words") or {}
sc = int(d.get("shardCount") or 0)
items = []
counts = [0] * max(sc, 1)
for key, val in words.items():
    wid, shard = val[0], int(val[1])
    reading, _, written = str(key).partition("|")
    items.append({"id": wid, "key": key, "reading": reading, "written": written or reading, "shard": shard})
    if 0 <= shard < len(counts):
        counts[shard] += 1
items.sort(key=lambda x: (x["shard"], x["reading"]))
out = {
    "version": 1,
    "status": "catalog",
    "engine": d.get("engine") or "supertonic-3-conj-delta-source",
    "language": "ja",
    "coverageRule": d.get("coverageRule"),
    "verbCount": int(d.get("verbCount") or 0),
    "uniqueReadingCount": int(d.get("uniqueReadingCount") or 0),
    "alreadyHostedReadingCount": int(d.get("alreadyHostedReadingCount") or 0),
    "newReadingCount": len(items),
    "capped": False,
    "cap": 0,
    "wordCount": len(items),
    "shardCount": sc,
    "shardCounts": counts,
    "voices": VOICES,
    "items": items,
    "words": words,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("Reconstructed", OUT, "items", len(items), "shards", sc, "voices", VOICES)
