#!/usr/bin/env python3
"""Build audited Traditional-Chinese vocabulary data using structured JMdict IDs.

Primary semantic source: Tomoshi open dictionary zh-TW definitions, joined by JMdict
entry_id. Core deck rows are resolved by exact written-form + reading. No meaning is
ever borrowed from a reading-only homophone or alternate spelling.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import build_vocab_bundle as base

ROOT = base.ROOT
ADV_OUT = ROOT / "data" / "advanced_vocab.js"
CORE_OUT = ROOT / "data" / "vocab_core_verified.js"
AUDIT_OUT = ROOT / "data" / "vocab_audit.json"
DB_PATH = Path(os.environ.get("TOMOSHI_DB", "/tmp/tomoshi.db"))
VALID_LEVELS = {"N1", "N2", "N3", "N4", "N5"}
MIN_ZH_CONFIDENCE = 0.65
MIN_COMMUNITY_LEVEL_CONFIDENCE = 0.75

# Corrections are keyed by (reading, displayed form), never by reading alone.
CURATED = {
    ("まい", "まい"): ("N2", "不會～；不打算～；恐怕不～（否定推量／否定意志）", "other"),
    ("まい", "舞"): ("N2", "舞；舞蹈", "noun"),
    ("まい", "枚"): ("N5", "張、枚（計算薄而平物件的量詞）", "noun"),
    ("まい", "毎"): ("N5", "每～；每一～", "other"),
    ("とりにく", "鶏肉"): ("N5", "雞肉", "noun"),
    ("とりにく", "とり肉"): ("N5", "雞肉", "noun"),
    ("ばからしい", "馬鹿らしい"): ("N2", "愚蠢的；無聊的；荒唐的", "adj"),
    ("ばからしい", "ばからしい"): ("N2", "愚蠢的；無聊的；荒唐的", "adj"),
}

NOISE_PREFIX = re.compile(r"^(?:[⓪①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳]|\d+[.．、])\s*")
POS_PREFIX = re.compile(r"^(?:【[^】]{1,18}】|\[[^\]]{1,18}\])\s*")


def exact_entry(raw: dict):
    entry = base.choose_entry(raw)
    if not entry:
        return None
    entry["forms"] = [entry["display"]]
    return entry


def parse_json_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    try:
        parsed = json.loads(value or "[]")
        return [str(x) for x in parsed] if isinstance(parsed, list) else []
    except Exception:
        return []


def clean_gloss(value: str) -> str:
    text = base.clean_text(value)
    text = NOISE_PREFIX.sub("", text)
    text = POS_PREFIX.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" ；;。")
    if not text or len(text) > 70:
        return ""
    if re.search(r"[\[\]{}<>]", text):
        return ""
    return text


def gloss_text(raw_glosses) -> str:
    out = []
    for raw in parse_json_list(raw_glosses):
        text = clean_gloss(raw)
        if text and text not in out:
            out.append(text)
        if len(out) >= 3:
            break
    return "；".join(out)[:100]


def load_tomoshi(conn: sqlite3.Connection):
    zh = {}
    zh_all = 0
    for row in conn.execute("SELECT entry_id, glosses, method, confidence FROM zh_defs_zhtw"):
        zh_all += 1
        confidence = float(row[3] or 0)
        meaning = gloss_text(row[1])
        if meaning and confidence >= MIN_ZH_CONFIDENCE:
            zh[int(row[0])] = (meaning, confidence, str(row[2] or ""))

    meta = {}
    for row in conn.execute("SELECT entry_id, jlpt_canonical, jlpt_level, is_common FROM entries"):
        meta[int(row[0])] = {
            "canonical": str(row[1] or ""),
            "level": int(row[2]) if row[2] is not None else None,
            "common": bool(row[3]),
        }

    community = {}
    for row in conn.execute("SELECT entry_id, n_level, source, confidence FROM vocab_jlpt"):
        community[int(row[0])] = (int(row[1]), str(row[2] or ""), float(row[3] or 0))
    return zh, meta, community, zh_all


def normalized_level(value) -> str:
    value = str(value or "").upper().strip()
    return value if value in VALID_LEVELS else ""


def level_for(entry_id: int | None, waller: str, original: str, rank: int,
              meta: dict, community: dict) -> tuple[str, str]:
    waller = normalized_level(waller)
    if waller:
        return waller, "jlpt-waller"
    if entry_id is not None:
        info = meta.get(entry_id) or {}
        canonical = normalized_level(info.get("canonical"))
        if canonical:
            return canonical, "tomoshi-canonical"
        comm = community.get(entry_id)
        if comm and comm[2] >= MIN_COMMUNITY_LEVEL_CONFIDENCE and 1 <= comm[0] <= 5:
            return f"N{comm[0]}", f"tomoshi-{comm[1] or 'community'}"
    original = normalized_level(original)
    if original:
        return original, "core-deck"
    return base.estimated_level(rank), "exact-frequency-estimate"


def parse_core_records(text: str) -> list[dict]:
    first = (text.splitlines()[:1] or [""])[0].strip().lower()
    delimiter = "," if first == "#separator:comma" else ";" if first == "#separator:semicolon" else "\t"
    records = []
    for row in csv.reader(io.StringIO(text), delimiter=delimiter):
        if not row or str(row[0] or "").strip().startswith("#"):
            continue
        if len(row) == 40:
            row = row[1:]
        elif len(row) == 38:
            row = [""] + row
        if len(row) != 39:
            continue
        display = base.clean_text(row[3]).replace(" ", "")
        reading = base.reading_from_furigana(row[6], display)
        meaning = base.clean_text(row[8])
        level_match = re.search(r"(?:^|[^A-Za-z0-9])N([1-5])(?=$|[^0-9])", f"{row[1]} {row[38]}", re.I)
        if not (display and reading and meaning and level_match):
            continue
        records.append({
            "display": display,
            "reading": reading,
            "key": f"{reading}|{display}",
            "meaning": meaning,
            "level": f"N{level_match.group(1)}",
        })
    # Preserve first occurrence exactly as runtime does.
    seen = set()
    return [r for r in records if not (r["key"] in seen or seen.add(r["key"]))]


def build_core_form_index(conn: sqlite3.Connection, core_keys: set[str]) -> dict[str, list[dict]]:
    result = defaultdict(list)
    for row in conn.execute("SELECT entry_id, text, reading, common, pri_rank, preferred FROM forms"):
        entry_id, text, reading, common, pri_rank, preferred = row
        key = f"{reading}|{text}"
        if key not in core_keys:
            continue
        result[key].append({
            "entry_id": int(entry_id),
            "common": int(common or 0),
            "pri_rank": int(pri_rank or 0),
            "preferred": int(preferred or 0),
        })
    return result


def choose_core_entry(options: list[dict], zh: dict, meta: dict) -> tuple[int | None, bool]:
    if not options:
        return None, False
    ids = {x["entry_id"] for x in options}
    ambiguous = len(ids) > 1
    ranked = sorted(options, key=lambda x: (
        1 if x["entry_id"] in zh else 0,
        zh.get(x["entry_id"], ("", 0, ""))[1],
        x["preferred"], x["common"],
        1 if (meta.get(x["entry_id"]) or {}).get("common") else 0,
        x["pri_rank"],
    ), reverse=True)
    if ambiguous:
        best = ranked[0]
        second = ranked[1]
        best_score = (
            best["entry_id"] in zh,
            round(zh.get(best["entry_id"], ("", 0, ""))[1], 2),
            best["preferred"], best["common"],
            bool((meta.get(best["entry_id"]) or {}).get("common")),
        )
        second_score = (
            second["entry_id"] in zh,
            round(zh.get(second["entry_id"], ("", 0, ""))[1], 2),
            second["preferred"], second["common"],
            bool((meta.get(second["entry_id"]) or {}).get("common")),
        )
        if best_score == second_score:
            return None, True
    return ranked[0]["entry_id"], ambiguous


def write_core_overlay(rows: list[list], meta: dict):
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    js = (
        "// AUTO-GENERATED by tools/build_vocab_bundle_exact.py. Do not edit by hand.\n"
        "(()=>{\"use strict\";\n"
        f"const M={meta_json},T={payload},map=new Map();\n"
        "for(const x of T)map.set(`${x[0]}|${x[1]}`,{level:x[2],meaning:x[3],meaningSource:x[4],levelSource:x[5],entryId:x[6]||null});\n"
        "window.VOCAB_CORE_VERIFIED=map;window.VOCAB_CORE_VERIFIED_META=M;\n"
        "})();\n"
    )
    CORE_OUT.write_text(js, encoding="utf-8")


def advanced_quality(item: dict):
    source_rank = 0 if item["meaning_source"] == "tomoshi-entry-id" else 1
    waller_rank = 0 if item["level_source"] == "jlpt-waller" else 1
    known_rank = 0 if item["rank"] < 999999 else 1
    common_rank = 0 if item.get("common") else 1
    return (source_rank, waller_rank, common_rank, known_rank, item["rank"], -item["meaning_confidence"], item["reading"])


def semantic_audit(all_rows: list[dict], fatal: list[dict]):
    by_display = defaultdict(list)
    for row in all_rows:
        by_display[row["display"]].append(row)

    forbidden = {
        "教え": ["學園", "学校", "學校"],
        "共和": ["西周"],
        "指令": ["歐洲聯盟指令"],
    }
    for display, bads in forbidden.items():
        for row in by_display.get(display, []):
            if any(bad in row["meaning"] for bad in bads):
                fatal.append({"type": "semantic_sentinel_failed", "display": display, "meaning": row["meaning"]})

    for display in ("仕上げ", "美人"):
        for row in by_display.get(display, []):
            if NOISE_PREFIX.search(row["meaning"]) or POS_PREFIX.search(row["meaning"]):
                fatal.append({"type": "meaning_markup_noise", "display": display, "meaning": row["meaning"]})
            if display == "美人" and row["meaning"].endswith("啊"):
                fatal.append({"type": "meaning_chat_noise", "display": display, "meaning": row["meaning"]})


def build() -> int:
    if not DB_PATH.exists():
        raise RuntimeError(f"Tomoshi SQLite database not found: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    print("Downloading JLPT core, JMdict-derived words, and frequency data...")
    core_text = base.fetch_text(base.URLS["core"])
    words_data = base.fetch_json(base.URLS["words"])
    try:
        freq_data = base.fetch_json(base.URLS["frequency"])
    except Exception as exc:
        print(f"warning: frequency source unavailable: {exc}")
        freq_data = {"entries": []}
    frequency = base.frequency_map(freq_data)
    core_records = parse_core_records(core_text)
    core_keys = {r["key"] for r in core_records}
    print(f"core unique rows: {len(core_records):,}")

    zh, tmeta, community, zh_total = load_tomoshi(conn)
    print(f"Tomoshi zh-TW rows: {zh_total:,}; accepted confidence >= {MIN_ZH_CONFIDENCE:.2f}: {len(zh):,}")

    waller_by_id = {}
    chosen_entries = []
    for raw in words_data.get("words") or []:
        try:
            eid = int(raw.get("id"))
        except Exception:
            eid = None
        if eid is not None:
            waller_by_id[eid] = normalized_level(raw.get("jlpt_waller"))
        entry = exact_entry(raw)
        if entry and eid is not None:
            entry["entry_id"] = eid
            chosen_entries.append(entry)

    # ---------- Core overlay: check every runtime core row ----------
    core_form_index = build_core_form_index(conn, core_keys)
    core_overlay = []
    core_audit = {
        "total": len(core_records), "exactEntryResolved": 0, "ambiguousPairs": 0,
        "unresolvedPairs": 0, "tomoshiMeaningsApplied": 0,
        "originalMeaningFallback": 0, "meaningChanged": 0, "levelChanged": 0,
    }
    ambiguous_samples = []
    unresolved_samples = []
    core_rows_for_audit = []
    for rec in core_records:
        options = core_form_index.get(rec["key"], [])
        eid, was_ambiguous = choose_core_entry(options, zh, tmeta)
        if was_ambiguous:
            core_audit["ambiguousPairs"] += 1
        if eid is None:
            core_audit["unresolvedPairs"] += 1
            if len(unresolved_samples) < 50:
                unresolved_samples.append(rec["key"])
        else:
            core_audit["exactEntryResolved"] += 1
        if was_ambiguous and len(ambiguous_samples) < 50:
            ambiguous_samples.append({"key": rec["key"], "candidateEntryIds": sorted({x["entry_id"] for x in options}), "selected": eid})

        meaning = rec["meaning"]
        meaning_source = "core-original-fallback"
        if eid in zh:
            meaning = zh[eid][0]
            meaning_source = "tomoshi-entry-id"
            core_audit["tomoshiMeaningsApplied"] += 1
        else:
            core_audit["originalMeaningFallback"] += 1

        rank = min(frequency.get(f"{rec['display']}|{rec['reading']}", 999999), frequency.get(rec["display"], 999999))
        level, level_source = level_for(eid, waller_by_id.get(eid, "") if eid else "", rec["level"], rank, tmeta, community)
        if meaning != rec["meaning"]:
            core_audit["meaningChanged"] += 1
        if level != rec["level"]:
            core_audit["levelChanged"] += 1
        core_overlay.append([rec["reading"], rec["display"], level, meaning, meaning_source, level_source, eid])
        core_rows_for_audit.append({"reading": rec["reading"], "display": rec["display"], "meaning": meaning, "level": level, "source": "core"})

    core_meta = {
        "version": "core-verified-20260826-v1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "rows": len(core_overlay),
        "meaningPolicy": "Tomoshi zh-TW by exact JMdict entry ID; exact form+reading resolution; original core meaning only when unresolved/missing",
        "levelPolicy": "JLPT Waller > Tomoshi canonical > high-confidence community > original core deck",
    }
    write_core_overlay(core_overlay, core_meta)

    # ---------- Advanced: only structured entry-ID meanings ----------
    candidates = {}
    for entry in chosen_entries:
        key = f"{entry['reading']}|{entry['display']}"
        if key in core_keys:
            continue
        eid = entry["entry_id"]
        z = zh.get(eid)
        if not z:
            continue
        rank = min(frequency.get(f"{entry['display']}|{entry['reading']}", 999999), frequency.get(entry["display"], 999999))
        level, level_source = level_for(eid, entry["raw"].get("jlpt_waller"), "", rank, tmeta, community)
        item = {
            "level": level, "reading": entry["reading"], "kanji": entry["kanji"],
            "display": entry["display"], "meaning": z[0], "pos": entry["pos"],
            "rank": rank, "key": key, "entry_id": eid, "meaning_confidence": z[1],
            "meaning_source": "tomoshi-entry-id", "level_source": level_source,
            "common": bool((tmeta.get(eid) or {}).get("common")),
        }
        prev = candidates.get(key)
        if prev is None or advanced_quality(item) < advanced_quality(prev):
            candidates[key] = item

    # Apply exact-key curated corrections and add missing sentinel/variant forms.
    for (reading, display), (level, meaning, pos) in CURATED.items():
        key = f"{reading}|{display}"
        if key in core_keys:
            continue
        if key in candidates:
            candidates[key].update(level=level, meaning=meaning, pos=pos, meaning_source="curated-exact", level_source="curated-exact", meaning_confidence=1.0)
        else:
            candidates[key] = {
                "level": level, "reading": reading, "kanji": display if base.CJK_RE.search(display) else "",
                "display": display, "meaning": meaning, "pos": pos, "rank": 999999,
                "key": key, "entry_id": None, "meaning_confidence": 1.0,
                "meaning_source": "curated-exact", "level_source": "curated-exact", "common": True,
            }

    ranked = sorted(candidates.values(), key=advanced_quality)
    if len(ranked) > 12500:
        ranked = ranked[:12500]
    merged_unique = len(core_keys | {x["key"] for x in ranked})
    if len(ranked) < 7000 or merged_unique <= 17000:
        raise RuntimeError(f"quality coverage gate failed: advanced={len(ranked):,}, merged={merged_unique:,}; need >=7,000 advanced and >17,000 merged")

    # ---------- Cross-dataset audit ----------
    fatal = []
    advanced_rows_for_audit = [{"reading": x["reading"], "display": x["display"], "meaning": x["meaning"], "level": x["level"], "source": "advanced"} for x in ranked]
    all_rows = core_rows_for_audit + advanced_rows_for_audit
    semantic_audit(all_rows, fatal)

    seen = set()
    homophones = defaultdict(list)
    mai = {"まい": [], "舞": [], "枚": [], "毎": []}
    negative = re.compile(r"(?:不(?:會|会|打算|可能|要)?|否定|絕不|绝不|恐怕不)")
    for row in all_rows:
        key = f"{row['reading']}|{row['display']}"
        if key in seen:
            fatal.append({"type": "duplicate_runtime_key", "key": key})
        seen.add(key)
        if row["level"] not in VALID_LEVELS or not row["meaning"]:
            fatal.append({"type": "invalid_runtime_row", "key": key})
        if row["reading"] == "まい" and row["display"] in mai:
            mai[row["display"]].append({"meaning": row["meaning"], "level": row["level"], "source": row["source"]})
            if row["display"] != "まい" and negative.search(row["meaning"]):
                fatal.append({"type": "mai_semantic_contamination", "key": key, "meaning": row["meaning"]})
        homophones[row["reading"]].append(row)

    variant_groups = []
    level_conflicts = []
    for reading, group in homophones.items():
        by_meaning = defaultdict(list)
        for row in group:
            by_meaning[row["meaning"]].append({"display": row["display"], "level": row["level"]})
        for meaning, forms in by_meaning.items():
            if len({x["display"] for x in forms}) > 1:
                rec = {"reading": reading, "meaning": meaning, "forms": forms}
                variant_groups.append(rec)
                if len({x["level"] for x in forms}) > 1:
                    level_conflicts.append(rec)
    for rec in level_conflicts:
        fatal.append({"type": "same_meaning_variant_level_conflict", **rec})

    counts = Counter(x["level"] for x in ranked)
    level_sources = Counter(x["level_source"] for x in ranked)
    meaning_sources = Counter(x["meaning_source"] for x in ranked)
    tuples = [[x["level"], x["reading"], x["kanji"], x["meaning"], x["pos"], x["level_source"], x["entry_id"]] for x in ranked]
    adv_meta = {
        "version": "prebuilt-20260826-v5-jmdict-id",
        "generated": datetime.now(timezone.utc).isoformat(),
        "generatedCount": len(tuples),
        "coreUniqueAtBuild": len(core_keys),
        "mergedUniqueAtBuild": merged_unique,
        "countsByLevel": {level: counts.get(level, 0) for level in ["N1", "N2", "N3", "N4", "N5"]},
        "meaningSources": dict(meaning_sources),
        "levelSources": dict(level_sources),
        "source": "JMdict-derived Japanese Language Data + Tomoshi zh-TW definitions joined by JMdict entry_id",
        "meaningPolicy": "structured JMdict entry-ID match; no reading/alternate-form semantic fallback",
        "levelPolicy": "JLPT Waller > Tomoshi canonical > high-confidence community > exact-form frequency estimate",
        "audit": "data/vocab_audit.json",
    }
    payload = json.dumps(tuples, ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(adv_meta, ensure_ascii=False, separators=(",", ":"))
    js = (
        "// AUTO-GENERATED by tools/build_vocab_bundle_exact.py. Do not edit by hand.\n"
        "// Meanings use structured JMdict-ID Traditional-Chinese definitions. Levels are third-party/estimated, not an official JLPT vocabulary list.\n"
        "(()=>{\"use strict\";\n"
        f"const M={meta_json},T={payload};\n"
        "window.ADVANCED_WORDS=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];\n"
        "const base=window.ADVANCED_WORDS.length;\n"
        "for(let i=0;i<T.length;i++){const x=T[i];window.ADVANCED_WORDS.push({id:`bundle-${i}`,level:x[0],reading:x[1],kanji:x[2]||\"\",displayWord:x[2]||x[1],meaning:x[3],pos:x[4]||\"other\",estimated:true,levelSource:x[5]||\"\",entryId:x[6]||null,source:\"進階補充詞（JMdict-ID 核對・推定等級）\"});}\n"
        "window.ADVANCED_WORDS_BUNDLE_META={...M,loadedCount:window.ADVANCED_WORDS.length-base};\n"
        "})();\n"
    )
    ADV_OUT.write_text(js, encoding="utf-8")

    audit = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "meaning": "Tomoshi Traditional-Chinese definitions joined by JMdict entry_id; core resolved by exact written form + reading; no homophone fallback",
            "level": "JLPT Waller > Tomoshi canonical > high-confidence community > core deck/exact frequency fallback",
            "officialJlptNote": "No official post-2010 JLPT per-word vocabulary list exists; site levels are learning labels from third-party sources or estimates.",
        },
        "counts": {
            "core": len(core_records), "advanced": len(ranked), "runtimeUnique": len(seen),
            "tomoshiZhRowsTotal": zh_total, "tomoshiZhAccepted": len(zh),
            "sameMeaningVariantGroups": len(variant_groups),
            "sameMeaningVariantLevelConflicts": len(level_conflicts),
        },
        "coreAudit": core_audit,
        "coreAmbiguousSamples": ambiguous_samples,
        "coreUnresolvedSamples": unresolved_samples,
        "advancedMeaningSources": dict(meaning_sources),
        "advancedLevelSources": dict(level_sources),
        "sentinelMai": mai,
        "variantGroups": variant_groups[:100],
        "levelConflicts": level_conflicts[:100],
        "semanticSentinels": ["教え", "共和", "指令", "仕上げ", "美人", "まい/舞/枚/毎"],
        "fatalIssueCount": len(fatal),
        "fatalIssues": fatal[:100],
    }
    AUDIT_OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if fatal:
        raise RuntimeError(f"vocabulary audit failed with {len(fatal)} fatal issue(s): {fatal[:5]}")

    print(json.dumps(audit, ensure_ascii=False, indent=2))
    print(f"wrote {ADV_OUT.relative_to(ROOT)} ({ADV_OUT.stat().st_size / 1024 / 1024:.2f} MiB)")
    print(f"wrote {CORE_OUT.relative_to(ROOT)} ({CORE_OUT.stat().st_size / 1024 / 1024:.2f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
