#!/usr/bin/env python3
"""Run the existing vocabulary builder with exact-form-only matching and emit an audit."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import build_vocab_bundle as base

ORIGINAL_CHOOSE = base.choose_entry

# Explicit corrections are keyed by (reading, displayed form), never by reading alone.
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


def choose_exact(raw: dict):
    entry = ORIGINAL_CHOOSE(raw)
    if entry:
        # Critical fix: the displayed lexical form is the ONLY semantic/frequency lookup key.
        # This prevents unrelated homophones from sharing a meaning or estimated rank.
        entry["forms"] = [entry["display"]]
    return entry


def parse_bundle(text: str):
    m = re.search(r"const M=(\{.*?\}),T=(\[.*\]);\nwindow\.ADVANCED_WORDS", text, flags=re.S)
    if not m:
        raise RuntimeError("Unable to parse generated advanced vocabulary bundle")
    return m, json.loads(m.group(1)), json.loads(m.group(2))


def dedupe_and_curate(tuples: list[list]):
    unique = []
    seen = set()
    removed = 0
    for row in tuples:
        if len(row) < 5:
            unique.append(row)
            continue
        level, reading, kanji, meaning, pos = row[:5]
        display = kanji or reading
        key = f"{reading}|{display}"
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        fix = CURATED.get((reading, display))
        if fix:
            level, meaning, pos = fix
        unique.append([level, reading, kanji, meaning, pos])
    return unique, removed


def ensure_curated(tuples: list[list], core_keys: set[str]):
    existing = {f"{row[1]}|{row[2] or row[1]}" for row in tuples if len(row) >= 5}
    added = []
    for (reading, display), (level, meaning, pos) in CURATED.items():
        key = f"{reading}|{display}"
        if key in existing or key in core_keys:
            continue
        tuples.append([level, reading, display if display != reading else "", meaning, pos])
        existing.add(key)
        added.append(key)
    return added


def audit(tuples: list[list], duplicate_rows_removed: int, core_keys: set[str], curated_added: list[str]) -> dict:
    fatal = []
    keys = set()
    homophones = defaultdict(list)
    sentinel = {"まい": [], "舞": [], "枚": [], "毎": []}
    negative = re.compile(r"(?:不(?:會|会|打算|可能|要)?|否定|絕不|绝不|恐怕不)")
    for row in tuples:
        if len(row) < 5:
            fatal.append({"type": "invalid_row", "row": row})
            continue
        level, reading, kanji, meaning, _pos = row[:5]
        display = kanji or reading
        key = f"{reading}|{display}"
        if key in keys:
            fatal.append({"type": "duplicate_key", "key": key})
        keys.add(key)
        if level not in {"N1", "N2", "N3", "N4", "N5"} or not reading or not display or not meaning:
            fatal.append({"type": "invalid_row", "key": key})
        homophones[reading].append((display, meaning, level))
        if reading == "まい" and display in sentinel:
            sentinel[display].append({"meaning": meaning, "level": level, "location": "advanced"})
            if display != "まい" and negative.search(str(meaning)):
                fatal.append({"type": "mai_semantic_contamination", "key": key, "meaning": meaning})

    core_presence = {display: f"まい|{display}" in core_keys for display in sentinel}
    variant_groups = []
    level_conflicts = []
    for reading, group in homophones.items():
        by_meaning = defaultdict(list)
        for display, meaning, level in group:
            by_meaning[meaning].append({"display": display, "level": level})
        for meaning, forms in by_meaning.items():
            if len({x["display"] for x in forms}) > 1:
                record = {"reading": reading, "meaning": meaning, "forms": forms}
                variant_groups.append(record)
                if len({x["level"] for x in forms}) > 1:
                    level_conflicts.append(record)

    for conflict in level_conflicts:
        fatal.append({"type": "same_meaning_variant_level_conflict", **conflict})

    return {
        "policy": {
            "meaning": "exact written-form match only; kana/alternate-form fallback forbidden",
            "level": "JLPT Waller when available; otherwise exact written-form+reading frequency only; curated exceptions are keyed by reading+written form",
            "officialJlptNote": "Estimated levels are not an official JLPT vocabulary list."
        },
        "counts": {
            "advancedGenerated": len(tuples),
            "uniqueKeys": len(keys),
            "duplicateRowsRemoved": duplicate_rows_removed,
            "sameMeaningVariantGroups": len(variant_groups),
            "sameMeaningVariantLevelConflicts": len(level_conflicts),
            "curatedRowsAdded": len(curated_added)
        },
        "sentinelMai": sentinel,
        "sentinelMaiCorePresence": core_presence,
        "curatedRowsAdded": curated_added,
        "variantGroups": variant_groups[:100],
        "levelConflicts": level_conflicts[:100],
        "fatalIssueCount": len(fatal),
        "fatalIssues": fatal[:100]
    }


def main() -> int:
    base.choose_entry = choose_exact
    rc = base.main()
    if rc:
        return rc

    out = Path(base.OUT)
    text = out.read_text(encoding="utf-8")
    match, meta, tuples = parse_bundle(text)
    tuples, removed = dedupe_and_curate(tuples)
    core_keys = base.core_keys(base.fetch_text(base.URLS["core"]))
    curated_added = ensure_curated(tuples, core_keys)
    # Apply curated corrections again to rows that may have just been added.
    tuples, removed_after_add = dedupe_and_curate(tuples)
    removed += removed_after_add
    report = audit(tuples, removed, core_keys, curated_added)
    if report["fatalIssueCount"]:
        raise RuntimeError(f"Vocabulary audit failed: {report['fatalIssues'][:5]}")

    counts = Counter(row[0] for row in tuples if len(row) >= 5)
    meta["version"] = "prebuilt-20260826-v4-exact"
    meta["generatedCount"] = len(tuples)
    meta["mergedUniqueAtBuild"] = len(core_keys | {f"{row[1]}|{row[2] or row[1]}" for row in tuples if len(row) >= 5})
    meta["countsByLevel"] = {level: counts.get(level, 0) for level in ["N1", "N2", "N3", "N4", "N5"]}
    meta["meaningPolicy"] = "exact written-form match only; no reading/alternate-form semantic fallback"
    meta["levelPolicy"] = "JLPT Waller when available; otherwise exact written-form+reading subtitle-frequency estimate; curated exceptions keyed by reading+form"
    meta["audit"] = "data/vocab_audit.json"
    replacement = "const M=" + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + ",T=" + json.dumps(tuples, ensure_ascii=False, separators=(",", ":")) + ";\nwindow.ADVANCED_WORDS"
    text = text[:match.start()] + replacement + text[match.end():]
    text = text.replace(
        "Advanced learning bands are estimated and are not an official JLPT vocabulary list.",
        "Meanings use exact written-form matching; estimated bands are not an official JLPT vocabulary list."
    )
    text = text.replace("進階補充詞（預先整理・推定等級）", "進階補充詞（精確詞形配對・推定等級）")
    out.write_text(text, encoding="utf-8")

    report["generatedCount"] = len(tuples)
    report["coreUniqueAtBuild"] = len(core_keys)
    report["mergedUniqueAtBuild"] = meta.get("mergedUniqueAtBuild")
    report["meaningSources"] = meta.get("meaningSources")
    audit_out = Path(base.ROOT) / "data" / "vocab_audit.json"
    audit_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
