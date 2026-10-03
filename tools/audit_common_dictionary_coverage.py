#!/usr/bin/env python3
"""Audit runtime vocabulary against common JMdict/Tomoshi dictionary entries.

This closes a deliberate gap in the older coverage audit: JLPT reference lists are
useful for level evidence, but they are not a complete general Japanese dictionary.
The audit therefore works at JMdict entry-ID level, so an already-covered spelling
variant counts as coverage for the same lemma and is not reported as a new word.

The report is review-only.  It never auto-publishes vocabulary. CI may run this
standalone or immediately after the teacher-audited vocabulary rebuild.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import build_vocab_bundle as base
import build_vocab_bundle_exact as exact
import recalibrate_jlpt_world as world

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("TOMOSHI_DB", "/tmp/tomoshi.db"))
TEACHER_TSV = ROOT / "data" / "jlpt_teacher_audit.tsv"
OUT = ROOT / "data" / "vocab_common_coverage_audit.json"
VALID_LEVELS = {"N1", "N2", "N3", "N4", "N5"}


def norm(value: object) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().replace(" ", "")


def normalized_level(value: object) -> str:
    text = str(value or "").upper().strip()
    if text in VALID_LEVELS:
        return text
    if text in {"1", "2", "3", "4", "5"}:
        return f"N{text}"
    return ""


def load_runtime_rows() -> list[dict]:
    if not TEACHER_TSV.exists():
        raise RuntimeError(f"teacher audit not found: {TEACHER_TSV}")
    with TEACHER_TSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    out = []
    for row in rows:
        reading, display = norm(row.get("reading")), norm(row.get("display"))
        if not reading or not display:
            continue
        out.append({
            "reading": reading,
            "display": display,
            "entry_id": str(row.get("entry_id") or "").strip(),
            "level": normalized_level(row.get("level")),
        })
    return out


def load_entries(conn: sqlite3.Connection):
    entries: dict[str, dict] = {}
    for eid, is_common, raw_data in conn.execute("SELECT id,is_common,data FROM entries"):
        eid = str(eid)
        try:
            data = json.loads(raw_data or "{}")
        except Exception:
            data = {}
        readings = {
            norm(x.get("text")) for x in (data.get("kana") or [])
            if isinstance(x, dict) and norm(x.get("text"))
        }
        entries[eid] = {
            "common": bool(is_common),
            "data": data,
            "readings": readings,
            "embedded_level": normalized_level(data.get("jlpt_level")),
        }
    return entries


def build_runtime_coverage(conn: sqlite3.Connection, runtime_rows: list[dict], entries: dict):
    by_display: dict[str, list[tuple[str, bool]]] = defaultdict(list)
    for text, eid, is_common in conn.execute("SELECT text,entry_id,is_common FROM forms"):
        display = norm(text)
        if display:
            by_display[display].append((str(eid), bool(is_common)))

    covered: set[str] = set()
    exact_resolved = 0
    ambiguous = 0
    unresolved = 0
    for row in runtime_rows:
        explicit = row["entry_id"]
        if explicit and explicit in entries:
            covered.add(explicit)
        candidates = []
        for eid, _form_common in by_display.get(row["display"], []):
            info = entries.get(eid) or {}
            if row["reading"] in (info.get("readings") or set()):
                candidates.append(eid)
        candidates = sorted(set(candidates))
        if len(candidates) == 1:
            covered.add(candidates[0])
            exact_resolved += 1
        elif len(candidates) > 1:
            # Conservative de-duplication: ambiguous homographs are not reported as
            # missing lemmas, because doing so would create false-positive additions.
            covered.update(candidates)
            ambiguous += 1
        else:
            unresolved += 1
    return covered, {
        "runtimeRows": len(runtime_rows),
        "exactResolvedRows": exact_resolved,
        "ambiguousRowsConservativelyCovered": ambiguous,
        "unresolvedRuntimeRows": unresolved,
    }


def preferred_entry(raw: dict):
    bad = base.BAD_TAGS
    kanji = [x for x in (raw.get("kanji") or []) if isinstance(x, dict)
             and not any(str(t) in bad for t in (x.get("tags") or []))]
    kana = [x for x in (raw.get("kana") or []) if isinstance(x, dict)
            and not any(str(t) in bad for t in (x.get("tags") or []))]
    if not kana:
        return None
    k = next((x for x in kanji if x.get("common")), kanji[0] if kanji else None)
    written = norm((k or {}).get("text"))
    matching = []
    for item in kana:
        applies = item.get("appliesToKanji") or []
        if not written or not applies or "*" in applies or written in applies:
            matching.append(item)
    if not matching:
        matching = kana
    r = next((x for x in matching if x.get("common")), matching[0])
    reading = norm(r.get("text"))
    display = written or reading
    if not reading or not display or not base.KANA_RE.fullmatch(reading) or not base.JAPANESE_RE.fullmatch(display):
        return None
    if len(display) > 22:
        return None

    senses = raw.get("sense") or raw.get("senses") or []
    pos_tags = []
    if isinstance(senses, dict):
        senses = list(senses.values())
    for sense in senses if isinstance(senses, list) else []:
        if not isinstance(sense, dict):
            continue
        pos_tags.extend(sense.get("partOfSpeech") or sense.get("pos") or [])
    pos = "other"
    if any(str(x).startswith("v") or str(x).startswith("vs") for x in pos_tags):
        pos = "verb"
    elif any(str(x).startswith("adj") for x in pos_tags):
        pos = "adj"
    elif any(str(x).startswith("adv") for x in pos_tags):
        pos = "adv"
    elif any(str(x).startswith("n") for x in pos_tags):
        pos = "noun"
    return {
        "reading": reading,
        "display": display,
        "pos": pos,
        "preferredWrittenCommon": bool((k or {}).get("common")),
        "preferredReadingCommon": bool(r.get("common")),
    }


def load_zh(conn: sqlite3.Connection) -> dict[str, str]:
    out = {}
    for eid, raw_data in conn.execute("SELECT entry_id,data FROM zh_defs_zhtw WHERE locale='zh-TW'"):
        meaning = exact.zh_meaning_from_data(raw_data)
        if meaning:
            out[str(eid)] = meaning
    return out


def load_direct_levels(conn: sqlite3.Connection, entries: dict) -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for eid, level, source in conn.execute("SELECT entry_id,level,source FROM vocab_jlpt"):
        level = normalized_level(level)
        if level:
            out[str(eid)] = (level, f"tomoshi-{str(source or 'community')}")
    for eid, info in entries.items():
        if eid not in out and info.get("embedded_level"):
            out[eid] = (info["embedded_level"], "tomoshi-entry-jlpt")
    return out


def main() -> int:
    if not DB.exists():
        raise RuntimeError(f"Tomoshi SQLite database not found: {DB}")
    conn = sqlite3.connect(str(DB))
    runtime = load_runtime_rows()
    entries = load_entries(conn)
    covered, coverage_meta = build_runtime_coverage(conn, runtime, entries)
    zh = load_zh(conn)
    direct_levels = load_direct_levels(conn, entries)
    _common_map, ranks = world.load_db_evidence(conn)

    common_ids = {eid for eid, info in entries.items() if info.get("common")}
    reviewable = []
    rejected_shape = 0
    missing_without_zh = 0
    for eid in sorted(common_ids - covered):
        info = entries[eid]
        pref = preferred_entry(info["data"])
        if not pref:
            rejected_shape += 1
            continue
        meaning = zh.get(eid, "")
        if not meaning:
            missing_without_zh += 1
            continue
        level, level_source = direct_levels.get(eid, ("", ""))
        rank = ranks.get(eid)
        reviewable.append({
            "entryId": eid,
            "reading": pref["reading"],
            "display": pref["display"],
            "meaning": meaning,
            "pos": pref["pos"],
            "directJlptLevel": level or None,
            "directJlptSource": level_source or None,
            "frequencyRank": rank,
            "preferredWrittenCommon": pref["preferredWrittenCommon"],
            "preferredReadingCommon": pref["preferredReadingCommon"],
            "reviewPriority": (
                "P1" if level and isinstance(rank, int) and rank <= 10000
                else "P2" if level or (isinstance(rank, int) and rank <= 10000)
                else "P3"
            ),
        })

    priority_order = {"P1": 0, "P2": 1, "P3": 2}
    reviewable.sort(key=lambda x: (
        priority_order[x["reviewPriority"]],
        x["frequencyRank"] if isinstance(x["frequencyRank"], int) else 10**12,
        len(x["display"]), x["reading"], x["display"],
    ))
    counts = Counter(x["reviewPriority"] for x in reviewable)
    report = {
        "version": "20261003-common-dictionary-entryid-v1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "status": "review_required" if reviewable else "complete",
        "scope": "Tomoshi/JMdict entries marked common, compared to complete runtime teacher audit at JMdict entry-ID level",
        "policy": {
            "variantDeduplication": "If any exact runtime form+reading resolves to the same JMdict entry ID, the lemma is covered; alternate spellings are not reported as missing words.",
            "ambiguity": "Ambiguous runtime homographs conservatively cover every matching entry ID to prevent false-positive additions.",
            "publication": "Report only; no candidate is automatically added to runtime vocabulary.",
            "meaning": "Traditional Chinese meaning must resolve through Tomoshi zh-TW for the same JMdict entry ID.",
        },
        "counts": {
            "runtimeRows": len(runtime),
            "dictionaryEntries": len(entries),
            "commonDictionaryEntries": len(common_ids),
            "coveredCommonEntryIds": len(common_ids & covered),
            "missingCommonEntryIdsRaw": len(common_ids - covered),
            "reviewableMissingCommonEntries": len(reviewable),
            "missingWithoutUsableZhTw": missing_without_zh,
            "missingRejectedByJapaneseShape": rejected_shape,
            "P1": counts.get("P1", 0),
            "P2": counts.get("P2", 0),
            "P3": counts.get("P3", 0),
        },
        "runtimeResolution": coverage_meta,
        "candidates": reviewable[:500],
        "candidateOutputLimit": 500,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["counts"], ensure_ascii=False))
    for x in reviewable[:30]:
        print(x["reviewPriority"], x["reading"], x["display"], x["directJlptLevel"], x["frequencyRank"], x["meaning"][:40])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
