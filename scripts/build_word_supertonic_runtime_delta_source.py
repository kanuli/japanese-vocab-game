#!/usr/bin/env python3
"""Build the exact current-runtime vocabulary delta for hosted Supertonic 3.

The teacher audit is the authoritative current word-list inventory.  Existing
baseline and v1 delta recordings are preserved; only exact reading|written keys
that are still missing are emitted for synthesis.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

AUDIT = Path(os.environ.get("TEACHER_AUDIT", "data/jlpt_teacher_audit.tsv"))
BASE = Path(os.environ.get("BASE_CATALOG", "word-supertonic3-catalog.json"))
DELTA1 = Path(os.environ.get("DELTA1_CATALOG", "word-supertonic3-delta-catalog.json"))
OUT = Path(os.environ.get("OUT", "word-supertonic3-runtime-delta-source.json"))
SHARDS = int(os.environ.get("SHARD_COUNT", "20"))


def load_words(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("status") != "ready" or not isinstance(data.get("words"), dict):
        raise SystemExit(f"Hosted catalog is not ready: {path}")
    return set(data["words"])


if SHARDS < 1:
    raise SystemExit("SHARD_COUNT must be positive")
if not AUDIT.is_file():
    raise SystemExit(f"Missing teacher audit: {AUDIT}")

runtime: dict[str, tuple[str, str]] = {}
with AUDIT.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f, delimiter="\t")
    required = {"reading", "display"}
    if not required.issubset(set(reader.fieldnames or [])):
        raise SystemExit(f"Teacher audit missing columns {sorted(required)}")
    for row in reader:
        reading = str(row.get("reading") or "").strip()
        display = str(row.get("display") or "").strip() or reading
        if not reading:
            raise SystemExit("Teacher audit contains an empty reading")
        key = f"{reading}|{display}"
        if key in runtime:
            raise SystemExit(f"Duplicate runtime exact key: {key}")
        runtime[key] = (reading, display)

if len(runtime) < 32000:
    raise SystemExit(f"Runtime vocabulary unexpectedly small: {len(runtime)}")

existing = load_words(BASE) | load_words(DELTA1)
missing = [key for key in runtime if key not in existing]
if not missing:
    raise SystemExit("No runtime Supertonic delta is required")

items = []
words = {}
counts = [0] * SHARDS
ids = set()
for key in sorted(missing):
    reading, written = runtime[key]
    wid = hashlib.sha256(("runtime-supertonic3-v2\0" + key).encode("utf-8")).hexdigest()[:16]
    if wid in ids:
        raise SystemExit(f"Recording ID collision: {wid}")
    ids.add(wid)
    shard = int(hashlib.sha256(wid.encode("utf-8")).hexdigest()[:8], 16) % SHARDS
    counts[shard] += 1
    items.append({"id": wid, "key": key, "reading": reading, "written": written, "shard": shard})
    words[key] = [wid, shard]

if any(n == 0 for n in counts):
    raise SystemExit(f"Unexpected empty runtime shard: {counts}")

out = {
    "version": 2,
    "status": "catalog",
    "engine": "supertonic-3-runtime-delta-source",
    "language": "ja",
    "coverageRule": "exact reading|written-form missing from baseline+delta-v1",
    "runtimeWordCount": len(runtime),
    "alreadyHostedExactCount": len(set(runtime) & existing),
    "wordCount": len(items),
    "shardCount": SHARDS,
    "shardCounts": counts,
    "items": items,
    "words": words,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print(json.dumps({k: out[k] for k in ("runtimeWordCount", "alreadyHostedExactCount", "wordCount", "shardCount", "shardCounts")}, ensure_ascii=False, indent=2))
