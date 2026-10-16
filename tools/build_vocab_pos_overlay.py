#!/usr/bin/env python3
"""Restore JMdict sense-level multi-POS by exact reviewed (reading, spelling, entry_id).

Source: Tomoshi open JMdict-derived database (CC BY-SA 4.0), pinned by workflow.
No phonetic-only homophone guessing, no Japanese ending->verb-group guessing.
Run: TOMOSHI_DB=/tmp/tomoshi.db python tools/build_vocab_pos_overlay.py
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data/jlpt_teacher_audit.tsv"
DB = Path(os.environ.get("TOMOSHI_DB", "/tmp/tomoshi.db"))
OUT = ROOT / "data/vocab_pos_verified.js"
REPORT = ROOT / "data/vocab_pos_audit.json"

ORDER = ("名詞", "代名詞", "動詞（第1類）", "動詞（第2類）",
         "動詞（第3類）", "い形容詞", "な形容詞",
         "副詞", "連體詞", "接續詞", "助詞", "助動詞",
         "感動詞", "助數詞", "接頭詞", "接尾詞", "慣用表現")
CODES = {"名詞": "n", "代名詞": "pn", "動詞（第1類）": "v1",
         "動詞（第2類）": "v2", "動詞（第3類）": "v3",
         "い形容詞": "i", "な形容詞": "na", "副詞": "adv",
         "連體詞": "adnom", "接續詞": "conj", "助詞": "prt",
         "助動詞": "aux", "感動詞": "int", "助數詞": "ctr",
         "接頭詞": "pref", "接尾詞": "suf", "慣用表現": "exp"}

def pos_to_labels(tags: list[str]) -> list[str]:
    out: set[str] = set()
    for raw in tags:
        t = str(raw or "").strip().lower()
        if t in {"n", "n-adv", "n-pref", "n-suf", "n-t", "n-pr", "n-common"}:
            out.add("名詞")
        elif t in {"pn"}:
            out.add("代名詞")
        elif t.startswith("v5") or t in {"v4h", "v4r", "v4k", "v4b", "v4m", "v4s", "v4t", "v4g", "v4n"}:
            out.add("動詞（第1類）")
        elif t.startswith("v1"):
            out.add("動詞（第2類）")
        elif t in {"vs", "vs-i", "vs-s", "vk", "vz"}:
            out.add("動詞（第3類）")
        elif t in {"adj-i", "adj-ix"}:
            out.add("い形容詞")
        elif t == "adj-na":
            out.add("な形容詞")
        elif t in {"adv", "adv-to"}:
            out.add("副詞")
        elif t in {"adj-pn", "adj-f", "adj-no", "adj-t"}:
            out.add("連體詞")
        elif t == "conj":
            out.add("接續詞")
        elif t == "prt":
            out.add("助詞")
        elif t in {"aux", "aux-v", "aux-adj"}:
            out.add("助動詞")
        elif t == "int":
            out.add("感動詞")
        elif t == "ctr":
            out.add("助數詞")
        elif t == "pref":
            out.add("接頭詞")
        elif t == "suf":
            out.add("接尾詞")
        elif t == "exp":
            out.add("慣用表現")
    return [tag for tag in ORDER if tag in out]

def applies(allowed: object, chosen: str) -> bool:
    # The JMdict-simplified schema uses ["*"] for unrestricted.
    if not isinstance(allowed, list) or not allowed:
        return True
    return "*" in allowed or chosen in allowed

def entry_labels(entry: dict, reading: str, display: str) -> list[str]:
    senses = entry.get("sense") or entry.get("senses") or []
    if isinstance(senses, dict):
        senses = list(senses.values())
    tags: list[str] = []
    for sense in senses:
        if not isinstance(sense, dict):
            continue
        if not applies(sense.get("appliesToKana"), reading):
            continue
        if not applies(sense.get("appliesToKanji"), display if display != reading else "*"):
            continue
        parts = sense.get("partOfSpeech") or sense.get("pos") or []
        tags.extend([parts] if isinstance(parts, str) else parts)
    return pos_to_labels(tags)

def generate(db: Path, audit: Path) -> tuple[list, dict]:
    with audit.open(encoding="utf-8", newline="") as f:
        words = list(csv.DictReader(f, delimiter="\t"))
    assert len(words) >= 32000, "Incomplete teacher exact-key audit"
    seen: set[str] = set()
    ids: dict[str, list] = {}
    for row in words:
        key = row["reading"] + "|" + row["display"]
        if key in seen:
            raise ValueError(f"Duplicate exact vocabulary key {key}")
        seen.add(key)
        eid = str(row.get("entry_id") or "").strip()
        if eid:
            ids.setdefault(eid, []).append(row)
    matched: list = []
    counts = Counter()
    missing = 0
    debug = []
    raw_tags = Counter()
    with sqlite3.connect(str(db)) as conn:
        # Read by primary-key from the same release used by vocabulary meanings.
        for eid, linked in ids.items():
            found = conn.execute("SELECT data FROM entries WHERE id=?", (eid,)).fetchone()
            if not found:
                missing += len(linked)
                continue
            try:
                entry = json.loads(found[0] or "{}")
            except (TypeError, json.JSONDecodeError):
                missing += len(linked)
                continue
            for row in linked:
                senses = entry.get("sense") or entry.get("senses") or []
                senses = senses.values() if isinstance(senses, dict) else senses
                for sense in senses:
                    if isinstance(sense, dict):
                        raw_tags.update(sense.get("partOfSpeech") or sense.get("pos") or [])
                labels = entry_labels(entry, row["reading"], row["display"])
                if not labels and len(debug) < 3:
                    senses = entry.get("sense") or entry.get("senses") or []
                    sample = (next(iter(senses.values()), {}) if isinstance(senses, dict)
                              else (senses[0] if isinstance(senses, list) and senses else {}))
                    debug.append({"id":eid, "entryKeys":list(entry.keys())[:15],
                                  "sense":str(sample)[:1100]})
                if labels:
                    codes = "".join(CODES[x] + "," for x in labels).rstrip(",")
                    matched.append([row["reading"], row["display"], codes])
                    for lab in labels:
                        counts[lab] += 1
                    if len(labels) > 1:
                        counts["multi"] += 1
                else:
                    missing += 1
    matched.sort(key=lambda x: (x[0], x[1]))
    report = {
        "source": "JMdict/Tomoshi CC BY-SA 4.0 (pinned structured database)",
        "auditRows": len(words), "entryIdRows": sum(len(v) for v in ids.values()),
        "verifiedRows": len(matched), "unresolvedRows": len(words) - len(matched),
        "missingOrUnrecognizedPOS": missing, "unresolvedSamples": debug,
        "verifiedLabels": dict(counts),
        "unresolvedPolicy": "Never fill missing POS with spelling-only conjectures",
        "rawPOSDistribution": raw_tags.most_common(60),
    }
    return matched, report

def main() -> None:
    if not DB.exists() or not AUDIT.exists():
        raise SystemExit(f"Required pinned dictionary or audit missing: {DB}, {AUDIT}")
    rows, report = generate(DB, AUDIT)
    if len(rows) < 18000:
        raise SystemExit(f"Insufficient exact dictionary POS coverage; no publication: {report}")
    data = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    js = (
        "// JMdict-derived POS; original EDRDG JMdict / Tomoshi (Y1Z), CC BY-SA 4.0.\n"
        "// Modified by mapping verified entry IDs to exact Japanese vocab display keys.\n"
        "// See data/VOCABULARY_DATA_NOTICE.md for sources, license and limitations.\n"
        "(function(root){'use strict';var a=" + data + ";var m=new Map();"
        "for(var i=0;i<a.length;i++)m.set(a[i][0]+'|'+a[i][1],a[i][2].split(','));"
        "root.VOCAB_POS_VERIFIED=m;"
        "root.VOCAB_POS_META=" + json.dumps(report, ensure_ascii=False, separators=(",", ":")) + ";"
        "})(typeof window!=='undefined'?window:globalThis);\n"
    )
    OUT.write_text(js, encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
if __name__ == "__main__":
    main()
