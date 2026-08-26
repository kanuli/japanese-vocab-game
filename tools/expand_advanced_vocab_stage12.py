#!/usr/bin/env python3
"""Stage 1+2 vocabulary expansion using the full reusable Tomoshi/JMdict corpus.

Stage 1 preserves the audited 12.5k advanced baseline generated immediately before
this script, then appends canonical learning forms selected directly from Tomoshi's
~217k JMdict entries. New rows require a reusable zh-TW meaning and learning evidence
(JLPT/common/frequency); exact form+reading collisions with conflicting entry senses
are skipped rather than guessed.

Stage 2 data from Mazii/MOJi/時雨 is validation-only. This script never scrapes or
copies those proprietary dictionaries. If data/vocab_stage2_external_validation.json
exists, its manually gathered presence/reading/level/sense-direction checks are merged
into the audit.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
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
STAGE2_OUT = ROOT / "data" / "vocab_stage2_external_validation.json"
TARGET = int(os.environ.get("VOCAB_ADVANCED_TARGET", "30000"))
BASELINE_EXPECTED = 12500
VALID_LEVELS = exact.VALID_LEVELS
BAD_MISC = {
    "arch", "archaic", "obs", "obsolete", "obsc", "rare", "dated", "hist", "historical",
    "dial", "dialect", "poet", "poetic", "vulg", "vulgar", "sl", "slang",
    "surname", "person", "given", "place", "company", "organization", "product",
}


def norm_text(value) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().replace(" ", "")


def normalized_level(value) -> str:
    return exact.normalized_level(value)


def parse_prebuilt_baseline() -> list[dict]:
    """Read the 12.5k exact-builder payload before overwriting it."""
    text = ADV_OUT.read_text(encoding="utf-8")
    marker = ",T="
    start = text.find(marker)
    if start < 0:
        raise RuntimeError("cannot find T payload in baseline advanced_vocab.js")
    start += len(marker)
    end = text.find(";\nwindow.ADVANCED_WORDS", start)
    if end < 0:
        end = text.find(";window.ADVANCED_WORDS", start)
    if end < 0:
        raise RuntimeError("cannot find end of baseline T payload")
    rows = json.loads(text[start:end])
    out = []
    for x in rows:
        if not isinstance(x, list) or len(x) < 5:
            continue
        level, reading, kanji, meaning, pos = map(lambda v: str(v or ""), x[:5])
        display = kanji or reading
        if not reading or not display or not meaning or level not in VALID_LEVELS:
            continue
        out.append({
            "level": level, "reading": reading, "kanji": kanji, "display": display,
            "meaning": meaning, "pos": pos or "other",
            "rank": 999999999, "key": f"{reading}|{display}",
            "entry_id": str(x[6]) if len(x) > 6 and x[6] else None,
            "meaning_source": "baseline-audited-tomoshi",
            "level_source": str(x[5]) if len(x) > 5 and x[5] else "baseline-audited",
            "common": False, "form_common": False, "quality_label": "BASELINE-audited",
        })
    if len(out) < 12000:
        raise RuntimeError(f"baseline parse unexpectedly small: {len(out)}")
    # Exact builder should already be unique, but keep the first safely if not.
    seen, unique = set(), []
    for item in out:
        if item["key"] not in seen:
            seen.add(item["key"]); unique.append(item)
    return unique


def parse_core_overlay() -> list[dict]:
    text = CORE_OUT.read_text(encoding="utf-8")
    m = re.search(r",T=(\[.*\]),map=new Map\(\);", text, re.S)
    if not m:
        raise RuntimeError("cannot parse generated core overlay")
    rows = json.loads(m.group(1))
    return [
        {"reading": str(x[0]), "display": str(x[1]), "level": str(x[2]),
         "meaning": str(x[3]), "source": "core-refined"}
        for x in rows if isinstance(x, list) and len(x) >= 4
    ]


def iter_senses(data: dict) -> list[dict]:
    senses = data.get("senses") or []
    if isinstance(senses, dict):
        def k(v):
            try: return int(v[0])
            except Exception: return 999999
        senses = [x[1] for x in sorted(senses.items(), key=k)]
    return [x for x in senses if isinstance(x, dict)] if isinstance(senses, list) else []


def flatten_tags(value) -> list[str]:
    out = []
    if isinstance(value, str):
        out.append(value)
    elif isinstance(value, dict):
        for v in value.values(): out.extend(flatten_tags(v))
    elif isinstance(value, list):
        for v in value: out.extend(flatten_tags(v))
    return out


def all_senses_low_value(data: dict) -> bool:
    senses = iter_senses(data)
    if not senses:
        return False
    good = 0
    for sense in senses:
        tags = set()
        for field in ("misc", "tags", "register", "dialect", "dial", "field"):
            for x in flatten_tags(sense.get(field)):
                token = re.sub(r"[^a-z]+", "", x.lower())
                if token: tags.add(token)
        if not tags.intersection(BAD_MISC):
            good += 1
    return good == 0


def pos_from_data(data: dict) -> str:
    values = []
    for sense in iter_senses(data)[:4]:
        for field in ("pos", "part_of_speech", "parts_of_speech"):
            values.extend(flatten_tags(sense.get(field)))
    s = " ".join(values).lower()
    if re.search(r"(?:^|\W)(?:v[1-5]|vs|vk|vz)(?:\W|$)|verb", s): return "verb"
    if "adjective" in s or re.search(r"(?:^|\W)adj", s): return "adj"
    if "adverb" in s or re.search(r"(?:^|\W)adv", s): return "adv"
    if "noun" in s or re.search(r"(?:^|\W)n(?:\W|$)", s): return "noun"
    return "other"


def form_restrictions(kana_item: dict) -> set[str]:
    for key in ("applies_to_kanji", "restrictions", "restrict", "kanji_restrictions", "re_restr"):
        value = kana_item.get(key)
        if isinstance(value, str) and value.strip(): return {norm_text(value)}
        if isinstance(value, list):
            vals = {norm_text(x.get("text") if isinstance(x, dict) else x) for x in value}
            vals.discard("")
            if vals: return vals
    return set()


def load_form_common(conn: sqlite3.Connection) -> dict[tuple[str, str], bool]:
    result = {}
    for text, eid, _is_kana, is_common in conn.execute("SELECT text, entry_id, is_kana, is_common FROM forms"):
        key = (str(eid), norm_text(text))
        result[key] = result.get(key, False) or bool(is_common)
    return result


def load_frequency(conn: sqlite3.Connection) -> tuple[dict[str, int], dict]:
    """Best-effort entry-id rank reader; schema is recorded for audit transparency."""
    try:
        cols = [str(r[1]) for r in conn.execute("PRAGMA table_info(freq_rank)")]
    except Exception:
        return {}, {"columns": [], "usable": False}
    if not cols:
        return {}, {"columns": [], "usable": False}
    lower = {c.lower(): i for i, c in enumerate(cols)}
    id_idx = next((lower[x] for x in ("entry_id", "entryid", "id") if x in lower), None)
    rank_idx = next((lower[x] for x in ("rank", "freq_rank", "frequency_rank") if x in lower), None)
    if id_idx is None or rank_idx is None:
        return {}, {"columns": cols, "usable": False}
    ranks = {}
    try:
        for row in conn.execute("SELECT * FROM freq_rank"):
            eid = str(row[id_idx] or "").strip()
            try: rank = int(row[rank_idx])
            except Exception: continue
            if eid and rank > 0:
                ranks[eid] = min(rank, ranks.get(eid, rank))
    except Exception:
        return {}, {"columns": cols, "usable": False}
    return ranks, {"columns": cols, "usable": True, "rows": len(ranks)}


def best_display(data: dict, eid: str, reading_item: dict, form_common: dict) -> tuple[str, str, bool]:
    reading = norm_text(reading_item.get("text"))
    if not reading:
        return "", "", False
    written = [x for x in (data.get("kanji") or []) if isinstance(x, dict) and norm_text(x.get("text"))]
    restrictions = form_restrictions(reading_item)
    if restrictions:
        restricted = [x for x in written if norm_text(x.get("text")) in restrictions]
        if restricted: written = restricted
    if not written:
        return reading, "", bool(form_common.get((eid, reading)))
    def key(x):
        text = norm_text(x.get("text"))
        intrinsic = bool(x.get("common") or x.get("is_common") or x.get("priority"))
        return (0 if form_common.get((eid, text)) else 1, 0 if intrinsic else 1, len(text), text)
    best = sorted(written, key=key)[0]
    display = norm_text(best.get("text"))
    return display, display, bool(form_common.get((eid, display)))


def explicit_level(eid: str, data: dict, tomoshi_jlpt: dict) -> tuple[str, str]:
    tj = tomoshi_jlpt.get(eid)
    if tj: return tj[0], f"tomoshi-{tj[1]}"
    embedded = normalized_level(data.get("jlpt_level"))
    if embedded: return embedded, "tomoshi-entry-jlpt"
    return "", ""


def quality_tier(item: dict) -> tuple[int, str]:
    direct = bool(item.get("direct_level"))
    common = bool(item.get("common"))
    rank = int(item.get("rank", 999999999))
    known = rank < 999999999
    if direct and common: return 0, "A-JLPT+common"
    if common and known: return 1, "B-common+frequency"
    if direct and known: return 2, "C-JLPT+frequency"
    if common: return 3, "D-common"
    if direct: return 4, "E-JLPT"
    if known and rank <= 20000: return 5, "F-frequency-top20k"
    if known and rank <= 50000: return 6, "G-frequency-top50k"
    if known: return 7, "H-frequency-observed"
    return 8, "I-open-dict-only"


def quality_key(item: dict):
    tier, label = quality_tier(item)
    return (tier, int(item.get("rank", 999999999)), 0 if item.get("common") else 1,
            item["reading"], item["display"], item.get("entry_id") or "")


def make_full_corpus_candidates(conn: sqlite3.Connection, blocked_keys: set[str]):
    zh, _entry_info, tomoshi_jlpt, zh_total = exact.load_tomoshi(conn)
    form_common = load_form_common(conn)
    freq, freq_meta = load_frequency(conn)
    by_key = defaultdict(list)
    stats = Counter()

    for row in conn.execute("SELECT id, is_common, data FROM entries"):
        eid = str(row[0])
        meaning = zh.get(eid)
        if not meaning:
            stats["excludedNoZh"] += 1; continue
        try: data = json.loads(row[2] or "{}")
        except Exception:
            stats["excludedBadJson"] += 1; continue
        if all_senses_low_value(data):
            stats["excludedAllLowValueSenses"] += 1; continue
        kana = [x for x in (data.get("kana") or []) if isinstance(x, dict) and norm_text(x.get("text"))]
        if not kana:
            stats["excludedNoReading"] += 1; continue
        # Canonical learner reading: prefer common indexed form, otherwise JMdict order.
        kana = sorted(enumerate(kana), key=lambda p: (
            0 if form_common.get((eid, norm_text(p[1].get("text")))) else 1,
            0 if (p[1].get("common") or p[1].get("is_common") or p[1].get("priority")) else 1,
            p[0]))
        reading_item = kana[0][1]
        reading = norm_text(reading_item.get("text"))
        display, kanji, display_common = best_display(data, eid, reading_item, form_common)
        if not reading or not display:
            stats["excludedNoCanonicalForm"] += 1; continue
        key = f"{reading}|{display}"
        if key in blocked_keys:
            stats["excludedExistingKey"] += 1; continue
        rank = int(freq.get(eid, 999999999))
        lvl, lvl_source = explicit_level(eid, data, tomoshi_jlpt)
        direct = bool(lvl)
        common = bool(row[1]) or display_common or bool(form_common.get((eid, reading)))
        if not lvl:
            lvl = base.estimated_level(rank)
            lvl_source = "tomoshi-priority-frequency-estimate" if rank < 999999999 else "common-entry-N1-estimate"
        item = {
            "level": lvl, "reading": reading, "kanji": kanji, "display": display,
            "meaning": meaning, "pos": pos_from_data(data), "rank": rank, "key": key,
            "entry_id": eid, "meaning_source": "tomoshi-entry-id-full-corpus",
            "level_source": lvl_source, "direct_level": direct,
            "common": common, "form_common": display_common,
        }
        tier, label = quality_tier(item)
        item["quality_label"] = label
        # Stage 1 deliberately excludes dictionary-only tail with no learner evidence.
        if tier >= 8:
            stats["excludedOpenDictionaryOnly"] += 1; continue
        by_key[key].append(item)
        stats["rawEvidenceCandidates"] += 1

    safe = []
    ambiguous = []
    for key, items in by_key.items():
        if len(items) == 1:
            safe.append(items[0]); continue
        meanings = {x["meaning"] for x in items}
        if len(meanings) == 1:
            safe.append(sorted(items, key=quality_key)[0]); stats["sameMeaningDuplicateKeysMerged"] += 1
            continue
        # Exact form+reading is lexically ambiguous across entries. Do not guess.
        ambiguous.append({"key": key, "entryIds": [x["entry_id"] for x in items],
                          "meanings": [x["meaning"] for x in items[:4]]})
        stats["excludedConflictingExactKeys"] += 1

    safe.sort(key=quality_key)
    return safe, ambiguous, {
        "tomoshiZhRowsTotal": zh_total, "tomoshiZhUsable": len(zh),
        "tomoshiJlptRows": len(tomoshi_jlpt), "frequency": freq_meta,
        **dict(stats), "safeSupplementCandidates": len(safe),
    }


def stage2_sample(added: list[dict]) -> list[dict]:
    if not added: return []
    n = len(added)
    indexes = []
    # Strong edge, middle, and quality boundary; 12 each where possible.
    for start in (0, max(0, n // 2 - 6), max(0, n - 12)):
        indexes.extend(range(start, min(n, start + 12)))
    out, seen = [], set()
    for i in indexes:
        if i in seen: continue
        seen.add(i); x = added[i]
        tier, label = quality_tier(x)
        out.append({
            "addedIndex": i, "key": x["key"], "reading": x["reading"], "display": x["display"],
            "meaning": x["meaning"], "level": x["level"], "pos": x["pos"], "entryId": x["entry_id"],
            "rank": None if x["rank"] >= 999999999 else x["rank"],
            "qualityTier": tier, "qualityTierLabel": label,
            "meaningSource": x["meaning_source"], "levelSource": x["level_source"],
        })
    return out


def write_bundle(selected: list[dict], core_count: int, source_stats: dict):
    counts = Counter(x["level"] for x in selected)
    levels = Counter(x["level_source"] for x in selected)
    meanings = Counter(x["meaning_source"] for x in selected)
    tiers = Counter(x.get("quality_label") or quality_tier(x)[1] for x in selected)
    tuples = [[x["level"], x["reading"], x["kanji"], x["meaning"], x["pos"],
               x["level_source"], x["entry_id"], x.get("quality_label", "")] for x in selected]
    meta = {
        "version": "prebuilt-20260826-v6-expanded-stage12",
        "generated": datetime.now(timezone.utc).isoformat(), "generatedCount": len(tuples),
        "coreUniqueAtBuild": core_count, "mergedUniqueAtBuild": core_count + len(tuples),
        "stage1Target": TARGET, "stage1BaselineAdvanced": BASELINE_EXPECTED,
        "stage1Added": max(0, len(tuples) - BASELINE_EXPECTED),
        "countsByLevel": {x: counts.get(x, 0) for x in ["N1","N2","N3","N4","N5"]},
        "qualityTierCounts": dict(tiers), "meaningSources": dict(meanings), "levelSources": dict(levels),
        "sourceStats": source_stats,
        "source": "Tomoshi open JMdict corpus + zh-TW definitions by JMdict entry_id; audited prior 12.5k preserved",
        "meaningPolicy": "reusable/open structured JMdict entry-ID meanings only; conflicting exact form+reading entries skipped",
        "stage2Policy": "Mazii/MOJi/時雨 are validation-only; no automated scraping or copied proprietary definitions",
        "audit": "data/vocab_audit.json",
    }
    payload = json.dumps(tuples, ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    ADV_OUT.write_text(
        "// AUTO-GENERATED by tools/expand_advanced_vocab_stage12.py. Do not edit by hand.\n"
        "// Full-corpus expansion uses reusable Tomoshi/JMdict data; proprietary web dictionaries are validation-only.\n"
        "(()=>{\"use strict\";\n" + f"const M={meta_json},T={payload};\n" +
        "window.ADVANCED_WORDS=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];const base=window.ADVANCED_WORDS.length;"
        "for(let i=0;i<T.length;i++){const x=T[i];window.ADVANCED_WORDS.push({id:`bundle-${i}`,level:x[0],reading:x[1],kanji:x[2]||\"\",displayWord:x[2]||x[1],meaning:x[3],pos:x[4]||\"other\",estimated:true,levelSource:x[5]||\"\",entryId:x[6]||null,qualityTier:x[7]||\"\",source:\"進階補充詞（Tomoshi/JMdict 開放全庫・品質分層）\"});}"
        "window.ADVANCED_WORDS_BUNDLE_META={...M,loadedCount:window.ADVANCED_WORDS.length-base};})();\n",
        encoding="utf-8")
    return meta


def reaudit(selected: list[dict], added: list[dict], safe_pool: list[dict], ambiguous: list[dict], source_stats: dict):
    core_rows = parse_core_overlay()
    advanced_rows = [{"reading":x["reading"],"display":x["display"],"meaning":x["meaning"],"level":x["level"],"source":"advanced-expanded"} for x in selected]
    all_rows = core_rows + advanced_rows
    semantic = []
    exact.semantic_audit(all_rows, semantic)
    fatal = [x for x in semantic if x.get("type") != "same_meaning_variant_level_conflict"]
    seen, homophones = set(), defaultdict(list)
    for row in all_rows:
        key=f"{row['reading']}|{row['display']}"
        if key in seen: fatal.append({"type":"duplicate_runtime_key","key":key})
        seen.add(key)
        if row["level"] not in VALID_LEVELS or not row["meaning"]:
            fatal.append({"type":"invalid_runtime_row","key":key})
        homophones[row["reading"]].append(row)
    variants, level_conflicts = [], []
    for reading, group in homophones.items():
        by_meaning=defaultdict(list)
        for row in group: by_meaning[row["meaning"]].append({"display":row["display"],"level":row["level"]})
        for meaning, forms in by_meaning.items():
            if len({x["display"] for x in forms})>1:
                rec={"reading":reading,"meaning":meaning,"forms":forms}; variants.append(rec)
                if len({x["level"] for x in forms})>1: level_conflicts.append(rec)
    if fatal:
        raise RuntimeError(f"expanded runtime semantic audit failed with {len(fatal)} blocking issue(s): {fatal[:10]}")

    audit=json.loads(AUDIT_OUT.read_text(encoding="utf-8"))
    sample=stage2_sample(added)
    tier_selected=Counter(x.get("quality_label") or quality_tier(x)[1] for x in selected)
    tier_added=Counter(x.get("quality_label") or quality_tier(x)[1] for x in added)
    boundary=added[-1] if added else None
    audit.setdefault("counts",{}).update({
        "advanced":len(selected), "runtimeUnique":len(seen),
        "sameMeaningVariantGroups":len(variants), "sameMeaningVariantLevelConflicts":len(level_conflicts),
        "orthographicVariantLevelDifferencesForReview":len(level_conflicts),
        "stage1AdvancedAddedVs12500":max(0,len(selected)-BASELINE_EXPECTED),
        "stage1SafeCandidatePool":len(safe_pool)+BASELINE_EXPECTED,
        "stage1ConflictingExactKeysSkipped":len(ambiguous),
        "stage2StratifiedReviewQueue":len(sample),
    })
    audit["stage1Expansion"]={
        "baselineAdvanced":BASELINE_EXPECTED,"targetAdvanced":TARGET,"selectedAdvanced":len(selected),
        "addedVsBaseline":max(0,len(selected)-BASELINE_EXPECTED),"runtimeUnique":len(seen),
        "safeSupplementCandidatePool":len(safe_pool),"qualityTierSelected":dict(tier_selected),
        "qualityTierAdded":dict(tier_added),"sourceStats":source_stats,
        "selectionRule":"preserve prior audited 12.5k; append canonical Tomoshi/JMdict rows with zh-TW and JLPT/common/frequency evidence; skip conflicting exact keys",
        "boundary":None if not boundary else {"key":boundary["key"],"rank":None if boundary["rank"]>=999999999 else boundary["rank"],"qualityTier":boundary.get("quality_label"),"level":boundary["level"]},
    }
    stage2={
        "status":"review-queue-generated",
        "policy":"Mazii/MOJi/時雨 are secondary manual validation only. No automated scraping/copying. Validate indexed presence, reading, learner level where visible, and sense direction; runtime meanings remain reusable Tomoshi/JMdict data.",
        "references":["Mazii","MOJi辞書","時雨日中辭典"],"reviewSample":sample,"validatedSample":[],
        "blockingConflicts":0,
    }
    if STAGE2_OUT.exists():
        try:
            ext=json.loads(STAGE2_OUT.read_text(encoding="utf-8"))
            if isinstance(ext,dict):
                stage2.update(ext)
                stage2.setdefault("reviewSample",sample)
        except Exception as exc:
            stage2["externalValidationLoadError"]=str(exc)
    audit["stage2ExternalValidation"]=stage2
    audit["expansionReviewIssueCount"]=len(level_conflicts)
    audit["expansionReviewIssues"]=[{"type":"orthographic_variant_level_difference",**x} for x in level_conflicts[:500]]
    audit["expansionFatalIssueCount"]=0
    audit["advancedMeaningSources"]=dict(Counter(x["meaning_source"] for x in selected))
    audit["advancedLevelSources"]=dict(Counter(x["level_source"] for x in selected))
    audit["advancedConflictingExactKeySamples"]=ambiguous[:100]
    audit.setdefault("policy",{})["advancedExpansion"]="Full Tomoshi/JMdict open corpus; prior 12.5k preserved; new canonical rows require reusable zh-TW plus learner evidence. Exact lexical ambiguity is skipped. Proprietary web dictionaries are validation-only."
    AUDIT_OUT.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"advanced":len(selected),"runtimeUnique":len(seen),"added":len(added),"supplementPool":len(safe_pool),"addedTiers":dict(tier_added),"boundary":audit["stage1Expansion"]["boundary"],"stage2Sample":len(sample),"conflictingSkipped":len(ambiguous)},ensure_ascii=False,indent=2))


def main()->int:
    if not DB_PATH.exists(): raise RuntimeError(f"Tomoshi SQLite database not found: {DB_PATH}")
    if not CORE_OUT.exists() or not AUDIT_OUT.exists() or not ADV_OUT.exists():
        raise RuntimeError("Run exact build and core refinement before Stage 1 expansion")
    baseline=parse_prebuilt_baseline()
    core_rows=parse_core_overlay()
    blocked={f"{x['reading']}|{x['display']}" for x in core_rows}|{x["key"] for x in baseline}
    conn=sqlite3.connect(str(DB_PATH))
    safe, ambiguous, source_stats=make_full_corpus_candidates(conn,blocked)
    needed=max(0,TARGET-len(baseline))
    if len(safe)<needed:
        raise RuntimeError(f"Stage 1 target unavailable after full-corpus evidence gate: baseline={len(baseline):,}, safe supplement={len(safe):,}, need={needed:,}, target={TARGET:,}")
    added=safe[:needed]
    selected=baseline+added
    write_bundle(selected,len(core_rows),source_stats)
    reaudit(selected,added,safe,ambiguous,source_stats)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
