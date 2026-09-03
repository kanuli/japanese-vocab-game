#!/usr/bin/env python3
from __future__ import annotations
import json, os, tarfile
from pathlib import Path

VOICE = os.environ.get("VOICE", "").strip()
SHARD = int(os.environ.get("SHARD", "-1"))
TAR = Path(os.environ["TAR"])
OUT = Path(os.environ.get("OUT", str(TAR.with_suffix(".json"))))
ENGINE = os.environ.get("ENGINE", "supertonic-3")
if not TAR.is_file():
    raise SystemExit(f"missing tar {TAR}")
members = {}
with tarfile.open(TAR, "r:") as tf:
    for x in tf.getmembers():
        if x.isfile():
            members[Path(x.name).stem] = [int(x.offset_data), int(x.size)]
manifest = {
    "version": 1,
    "engine": ENGINE,
    "voice": VOICE,
    "shard": SHARD,
    "count": len(members),
    "asset": TAR.name,
    "members": members,
    "rebuiltFromTar": True,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("Wrote", OUT, "members", len(members))
