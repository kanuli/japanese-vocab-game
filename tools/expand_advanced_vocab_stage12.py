#!/usr/bin/env python3
"""Stage 1 vocabulary expansion from reusable JMdict/Tomoshi data.

This script intentionally does NOT scrape Mazii, MOJi, or 時雨. Those services are
used only for secondary manual/stratified validation in Stage 2 because their terms
do not grant bulk-copy rights. The runtime vocabulary itself is generated only from
reusable/open sources already used by the project.

Run after build_vocab_bundle_exact.py and refine_core_ambiguity.py. It expands the
advanced bundle to a quality-ranked target, re-audits every runtime key, and writes a
stratified boundary sample into vocab_audit.json for Stage 2 cross-checking.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import build_vocab_bundle as base
import build_vocab_bundle_exact as exact

ROOT = base.ROOT
DB_PATH = Path(os.environ.get("TOMOSHI_DB", "/tmp/tomoshi.db"))
ADV_OUT = ROOT / "data" / "advanced_vocab.js"
CORE_OUT = ROOT / "data" / "vocab_core_verified.js"
AUDIT_OUT = ROOT / "data" / "vocab_audit.json"
TARGET = int(os.environ.get("VOCAB_ADVANCED_TARGET", "30000"))
BASELINE = 12500
VALID_LEVELS = exact.VALID_LEVELS


def quality_tier(item: dict) -> tuple[int, str]:
    """Learning-oriented quality tier; lower is stronger evidence."""
    direct = item["level_source"] != "exact-frequency-estimate"
    known_rank = item["rank"] < 999999
    common = bool(item.get("common"))
    rank = item["rank"]
    if direct and common:
        return 0, "A-direct-level+common"
    if common and known_rank:
        return 1, "B-common+frequency"
    if direct and known_rank:
        return 2, "C-direct-level+frequency"
    if direct:
        return 3, "D-direct-level"
    if known_rank and rank <= 20000:
        return 4, "E-frequency-top20k"
    if common:
        return 5, "F-common"
    if known_rank and rank <= 50000:
        return 6, "G-frequency-top50k"
    if known_rank:
        return 7, "H-frequency-observed"
    return 8, "I-open-dict-only"


def quality_key(item: dict):
    tier, _ = quality_tier(item)
    return (
        tier,
        item["rank"],
        0 if item.get("common") else 1,
        item["reading"],
        item["display"],
        item["entry_id"] or "",
    )


def parse_core_overlay() -> list[dict]:
    text = CORE_OUT.read_text(encoding="utf-8")
    m = re.search(r",T=(\[.*\]),map=new Map\(\);", text, re.S)
    if not m:
        raise RuntimeError("cannot parse generated core overlay")
    rows = json.loads(m.group(1))
    out = []
    for x in rows:
        if not isinstance(x, list) or len(x) < 4:
            continue
        out.append({
            "reading": str(x[0]), "display": str(x[1]), "level": str(x[2]),
            "meaning": str(x[3]), "source": "core-refined"
        })
    return out


def sample_rows(added: list[dict]) -> list[dict]:
    """Stratified Stage-2 review sample from start/middle/tail of the expansion."""
    if not added:
        return []
    positions = []
    n = len(added)
    for start in (0, max(0, n // 2 - 6), max(0, n - 12)):
        positions.extend(range(start, min(n, start + 12)))
    seen = set()
    out = []
    for idx in positions:
        if idx in seen:
            continue
        seen.add(idx)
        x = added[idx]
        tier, label = quality_tier(x)
        out.append({
            "expansionIndex": BASELINE + idx,
            "key": x["key"], "reading": x["reading"], "display": x["display"],
            "meaning": x["meaning"], "level": x["level"], "pos": x["pos"],
            "entryId": x["entry_id"], "rank": None if x["rank"] >= 999999 else x["rank"],
            "qualityTier": tier, "qualityTierLabel": label,
            "meaningSource": x["meaning_source"], "levelSource": x["level_source"],
        })
    return out


def build_candidates(conn: sqlite3.Connection):
    core_text = base.fetch_text(base.URLS["core"])
    core_records = exact.parse_core_records(core_text)
    core_keys = {r["key"] for r in core_records}

    words_data = base.fetch_json(base.URLS["words"])
    try:
        freq_data = base.fetch_json(base.URLS["frequency"])
    except Exception as exc:
        print(f"warning: frequency source unavailable: {exc}")
        freq_data = {"entries": []}
    frequency = base.frequency_map(freq_data)
    zh, entry_info, tomoshi_jlpt, zh_total = exact.load_tomoshi(conn)

    candidates: dict[str, dict] = {}
    duplicate_entry_keys = defaultdict(set)
    raw_eligible = 0
    excluded_core = 0
    excluded_no_zh = 0
    waller_by_id = {}

    for raw in words_data.get("words") or []:
        eid = str(raw.get("id") or "").strip()
        if not eid:
            continue
        waller_by_id[eid] = exact.normalized_level(raw.get("jlpt_waller"))
        entry = exact.exact_entry(raw)
        if not entry:
            continue
        entry["entry_id"] = eid
        key = f"{entry['reading']}|{entry['display']}"
        if key in core_keys:
            excluded_core += 1
            continue
        meaning = zh.get(eid)
        if not meaning:
            excluded_no_zh += 1
            continue
        raw_eligible += 1
        rank = min(
            frequency.get(f"{entry['display']}|{entry['reading']}", 999999),
            frequency.get(entry["display"], 999999),
        )
        level, level_source = exact.level_for(
            eid, raw.get("jlpt_waller"), "", rank, entry_info, tomoshi_jlpt
        )
        item = {
            "level": level, "reading": entry["reading"], "kanji": entry["kanji"],
            "display": entry["display"], "meaning": meaning, "pos": entry["pos"],
            "rank": rank, "key": key, "entry_id": eid,
            "meaning_source": "tomoshi-entry-id", "level_source": level_source,
            "common": bool((entry_info.get(eid) or {}).get("common")),
        }
        duplicate_entry_keys[key].add(eid)
        prev = candidates.get(key)
        if prev is None or quality_key(item) < quality_key(prev):
            candidates[key] = item

    for (reading, display), (level, meaning, pos) in exact.CURATED.items():
        key = f"{reading}|{display}"
        if key in core_keys:
            continue
        if key in candidates:
            candidates[key].update(
                level=level, meaning=meaning, pos=pos,
                meaning_source="curated-exact", level_source="curated-exact", common=True,
            )
        else:
            candidates[key] = {
                "level": level, "reading": reading,
                "kanji": display if base.CJK_RE.search(display) else "",
                "display": display, "meaning": meaning, "pos": pos,
                "rank": 999999, "key": key, "entry_id": None,
                "meaning_source": "curated-exact", "level_source": "curated-exact",
                "common": True,
            }

    ranked_all = sorted(candidates.values(), key=quality_key)
    if len(ranked_all) < TARGET:
        raise RuntimeError(
            f"Stage 1 target unavailable: only {len(ranked_all):,} safe structured candidates; target={TARGET:,}"
        )
    ranked = ranked_all[:TARGET]

    return ranked, ranked_all, core_records, {
        "zhTotal": zh_total, "zhUsable": len(zh), "rawEligible": raw_eligible,
        "uniqueCandidates": len(candidates), "excludedCore": excluded_core,
        "excludedNoZh": excluded_no_zh,
        "multiEntryExactKeys": sum(1 for v in duplicate_entry_keys.values() if len(v) > 1),
    }


def write_bundle(ranked: list[dict], core_count: int, source_stats: dict):
    counts = Counter(x["level"] for x in ranked)
    level_sources = Counter(x["level_source"] for x in ranked)
    meaning_sources = Counter(x["meaning_source"] for x in ranked)
    tier_counts = Counter(quality_tier(x)[1] for x in ranked)
    tuples = [
        [x["level"], x["reading"], x["kanji"], x["meaning"], x["pos"],
         x["level_source"], x["entry_id"], quality_tier(x)[1]]
        for x in ranked
    ]
    meta = {
        "version": "prebuilt-20260826-v6-expanded-stage12",
        "generated": datetime.now(timezone.utc).isoformat(),
        "generatedCount": len(tuples), "coreUniqueAtBuild": core_count,
        "mergedUniqueAtBuild": core_count + len(tuples),
        "stage1Target": TARGET, "stage1BaselineAdvanced": BASELINE,
        "stage1Added": max(0, len(tuples) - BASELINE),
        "countsByLevel": {level: counts.get(level, 0) for level in ["N1", "N2", "N3", "N4", "N5"]},
        "qualityTierCounts": dict(tier_counts),
        "meaningSources": dict(meaning_sources), "levelSources": dict(level_sources),
        "sourceStats": source_stats,
        "source": "JMdict-derived Japanese Language Data + Tomoshi open zh-TW definitions by JMdict entry_id",
        "meaningPolicy": "reusable/open structured JMdict entry-ID match only; no proprietary web-dictionary bulk ingest",
        "levelPolicy": "community JLPT/Tomoshi entry level > exact subtitle-frequency estimate",
        "stage2Policy": "Mazii/MOJi/時雨 are secondary stratified/manual validation references only; no scraping or copied dictionary text",
        "audit": "data/vocab_audit.json",
    }
    payload = json.dumps(tuples, ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    ADV_OUT.write_text(
        "// AUTO-GENERATED by tools/expand_advanced_vocab_stage12.py. Do not edit by hand.\n"
        "// Expanded from reusable JMdict/Tomoshi data. External proprietary dictionaries are validation-only.\n"
        "(()=>{\"use strict\";\n" + f"const M={meta_json},T={payload};\n" +
        "window.ADVANCED_WORDS=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];const base=window.ADVANCED_WORDS.length;"
        "for(let i=0;i<T.length;i++){const x=T[i];window.ADVANCED_WORDS.push({id:`bundle-${i}`,level:x[0],reading:x[1],kanji:x[2]||\"\",displayWord:x[2]||x[1],meaning:x[3],pos:x[4]||\"other\",estimated:true,levelSource:x[5]||\"\",entryId:x[6]||null,qualityTier:x[7]||\"\",source:\"進階補充詞（JMdict/Tomoshi 開放資料・品質分層）\"});}"
        "window.ADVANCED_WORDS_BUNDLE_META={...M,loadedCount:window.ADVANCED_WORDS.length-base};})();\n",
        encoding="utf-8",
    )
    return meta


def reaudit(ranked: list[dict], ranked_all: list[dict], core_records: list[dict], meta: dict):
    core_rows = parse_core_overlay()
    advanced_rows = [
        {"reading": x["reading"], "display": x["display"], "meaning": x["meaning"],
         "level": x["level"], "source": "advanced-expanded"}
        for x in ranked
    ]
    all_rows = core_rows + advanced_rows
    fatal = []
    exact.semantic_audit(all_rows, fatal)
    seen = set()
    homophones = defaultdict(list)
    for row in all_rows:
        key = f"{row['reading']}|{row['display']}"
        if key in seen:
            fatal.append({"type": "duplicate_runtime_key", "key": key})
        seen.add(key)
        if row["level"] not in VALID_LEVELS or not row["meaning"]:
            fatal.append({"type": "invalid_runtime_row", "key": key})
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

    if fatal:
        raise RuntimeError(f"expanded runtime semantic audit failed: {fatal[:10]}")

    baseline_keys = {x["key"] for x in ranked[:min(BASELINE, len(ranked))]}
    added = [x for x in ranked if x["key"] not in baseline_keys]
    tier_all = Counter(quality_tier(x)[1] for x in ranked_all)
    tier_selected = Counter(quality_tier(x)[1] for x in ranked)
    boundary = ranked[-1] if ranked else None

    audit = json.loads(AUDIT_OUT.read_text(encoding="utf-8"))
    audit.setdefault("counts", {})["advanced"] = len(ranked)
    audit["counts"]["runtimeUnique"] = len(seen)
    audit["counts"]["sameMeaningVariantGroups"] = len(variant_groups)
    audit["counts"]["sameMeaningVariantLevelConflicts"] = len(level_conflicts)
    audit["counts"]["stage1AdvancedAddedVs12500"] = max(0, len(ranked) - BASELINE)
    audit["counts"]["stage1SafeCandidatePool"] = len(ranked_all)
    audit["counts"]["stage2StratifiedReviewQueue"] = len(sample_rows(added))
    audit["advancedMeaningSources"] = dict(Counter(x["meaning_source"] for x in ranked))
    audit["advancedLevelSources"] = dict(Counter(x["level_source"] for x in ranked))
    audit["stage1Expansion"] = {
        "baselineAdvanced": BASELINE, "targetAdvanced": TARGET,
        "selectedAdvanced": len(ranked), "addedVsBaseline": max(0, len(ranked) - BASELINE),
        "runtimeUnique": len(seen), "safeCandidatePool": len(ranked_all),
        "qualityTierSelected": dict(tier_selected), "qualityTierAvailable": dict(tier_all),
        "selectionRule": "BAD_TAGS exclusion + reusable zh-TW entry-ID meaning + quality tiers using JLPT/common/frequency evidence",
        "boundary": None if not boundary else {
            "key": boundary["key"], "rank": None if boundary["rank"] >= 999999 else boundary["rank"],
            "qualityTier": quality_tier(boundary)[1], "level": boundary["level"],
        },
    }
    audit["stage2ExternalValidation"] = {
        "status": "review-queue-generated",
        "policy": "No automated scraping/copying of Mazii, MOJi or 時雨. Use the three sites only to validate presence, reading, learner level and sense selection on a stratified/high-risk sample; runtime meanings remain from reusable open data or independently written exact corrections.",
        "references": ["Mazii", "MOJi辞書", "時雨日中辭典"],
        "reviewSample": sample_rows(added),
        "validatedSample": [],
    }
    audit["expansionReviewIssueCount"] = len(level_conflicts)
    audit["expansionReviewIssues"] = [
        {"type": "orthographic_variant_level_difference", **x} for x in level_conflicts[:500]
    ]
    audit["expansionFatalIssueCount"] = 0
    audit["counts"]["orthographicVariantLevelDifferencesForReview"] = len(level_conflicts)
    audit.setdefault("policy", {})["advancedExpansion"] = (
        "Stage 1 expands only from reusable JMdict/Tomoshi entry-ID data. Entries tagged archaic/obsolete/rare/proper-name etc. are excluded by the base JMdict filter. "
        "Selection is quality-tiered by direct community JLPT evidence, commonness and exact subtitle-frequency evidence. Stage 2 proprietary web dictionaries are validation-only."
    )
    AUDIT_OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selectedAdvanced": len(ranked), "runtimeUnique": len(seen),
        "addedVsBaseline": max(0, len(ranked) - BASELINE),
        "safeCandidatePool": len(ranked_all),
        "selectedTiers": dict(tier_selected),
        "boundary": audit["stage1Expansion"]["boundary"],
        "stage2ReviewSample": len(audit["stage2ExternalValidation"]["reviewSample"]),
        "variantLevelReview": len(level_conflicts),
    }, ensure_ascii=False, indent=2))


def main() -> int:
    if not DB_PATH.exists():
        raise RuntimeError(f"Tomoshi SQLite database not found: {DB_PATH}")
    if not CORE_OUT.exists() or not AUDIT_OUT.exists():
        raise RuntimeError("Run exact build and core refinement before Stage 1 expansion")
    conn = sqlite3.connect(str(DB_PATH))
    ranked, ranked_all, core_records, source_stats = build_candidates(conn)
    meta = write_bundle(ranked, len(core_records), source_stats)
    reaudit(ranked, ranked_all, core_records, meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
