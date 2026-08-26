#!/usr/bin/env python3
"""Run the existing vocabulary builder with exact-form-only matching and emit an audit."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import build_vocab_bundle as base

ORIGINAL_CHOOSE = base.choose_entry


def choose_exact(raw: dict):
    entry = ORIGINAL_CHOOSE(raw)
    if entry:
        # Critical fix: the displayed lexical form is the ONLY semantic/frequency lookup key.
        # This prevents 舞 / 枚 / 毎 from inheriting the kana-only ～まい meaning or rank.
        entry["forms"] = [entry["display"]]
    return entry


def parse_bundle(text: str):
    m = re.search(r"const M=(\{.*?\}),T=(\[.*\]);\nwindow\.ADVANCED_WORDS", text, flags=re.S)
    if not m:
        raise RuntimeError("Unable to parse generated advanced vocabulary bundle")
    return m, json.loads(m.group(1)), json.loads(m.group(2))


def audit(tuples: list[list]) -> dict:
    fatal = []
    keys = set()
    homophones = defaultdict(list)
    sentinel = {"舞": [], "枚": [], "毎": []}
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
            sentinel[display].append({"meaning": meaning, "level": level})
            if negative.search(str(meaning)):
                fatal.append({"type": "mai_semantic_contamination", "key": key, "meaning": meaning})

    review_groups = 0
    for group in homophones.values():
        by_meaning = defaultdict(set)
        for display, meaning, _level in group:
            by_meaning[meaning].add(display)
        if any(len(forms) > 1 for forms in by_meaning.values()):
            review_groups += 1

    return {
        "policy": {
            "meaning": "exact written-form match only; kana/alternate-form fallback forbidden",
            "level": "JLPT Waller when available; otherwise exact written-form+reading frequency only",
            "officialJlptNote": "Estimated levels are not an official JLPT vocabulary list."
        },
        "counts": {
            "advancedGenerated": len(tuples),
            "uniqueKeys": len(keys),
            "sameMeaningHomophoneGroupsForReview": review_groups
        },
        "sentinelMai": sentinel,
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
    report = audit(tuples)
    if report["fatalIssueCount"]:
        raise RuntimeError(f"Vocabulary audit failed: {report['fatalIssues'][:5]}")

    meta["version"] = "prebuilt-20260826-v4-exact"
    meta["meaningPolicy"] = "exact written-form match only; no reading/alternate-form semantic fallback"
    meta["levelPolicy"] = "JLPT Waller when available; otherwise exact written-form+reading subtitle-frequency estimate"
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
    report["coreUniqueAtBuild"] = meta.get("coreUniqueAtBuild")
    report["mergedUniqueAtBuild"] = meta.get("mergedUniqueAtBuild")
    report["meaningSources"] = meta.get("meaningSources")
    audit_out = Path(base.ROOT) / "data" / "vocab_audit.json"
    audit_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
