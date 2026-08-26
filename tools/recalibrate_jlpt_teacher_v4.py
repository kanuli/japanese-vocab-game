#!/usr/bin/env python3
"""Teacher-style JLPT vocabulary audit v4.

Audit every runtime vocabulary row by exact (reading, display) key.  JLPT does not
publish an official post-2010 word-by-word vocabulary list, so this script records
both the selected learning level and how confidently that level can be defended.

Teacher policy, in order:
  1. Exact curated/manual checks are authoritative.
  2. The original N1-N5 core-deck exact key is the baseline for core learning words.
     An unrelated spelling of the same JMdict entry may NOT promote/demote it.
  3. Exact OpenJLPT and exact Waller/Tanos evidence corroborate or challenge the
     baseline.  Same-entry evidence is audit context only, never a deciding vote.
  4. Normalized equivalents are used only for mechanical spelling artefacts such as
     bracketed furigana (e.g. 石鹸[けん] -> 石鹸), never arbitrary homophones.
  5. Conflicting exact evidence is resolved conservatively and marked for review.
  6. Only rows with no usable direct evidence are estimated.  Estimated N1 requires
     positive rarity evidence and is never created by a missing frequency rank.

Every row is written to data/jlpt_teacher_audit.tsv with its level, grade, basis,
conflict state and evidence so the result is inspectable word-by-word.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import build_vocab_bundle as base
import build_vocab_bundle_exact as exact
import recalibrate_jlpt_world as v1
import recalibrate_jlpt_world_v2 as v2

ROOT = Path(__file__).resolve().parents[1]
LEVELS = v1.LEVELS
VALID = v1.VALID
IDX = {x: i for i, x in enumerate(LEVELS)}
TEACHER_AUDIT = ROOT / "data" / "jlpt_teacher_audit.tsv"

# High-confidence teacher anchors. These include user-reported regressions and very
# basic vocabulary whose accidental promotion would invalidate the learning levels.
TEACHER_ANCHORS = {
    "まい|まい": "N2",
    "まい|舞": "N2",
    "まい|枚": "N5",
    "まい|毎": "N5",
    "すいか|西瓜": "N5",
    "これ|これ": "N5",
    "それ|それ": "N5",
    "おもしろい|面白い": "N5",
    "あかるい|明るい": "N5",
    "おわる|終わる": "N5",
    "べんきょう|勉強": "N5",
    "さんぽ|散歩": "N5",
    "だんだん|だんだん": "N5",
    "もし|もし": "N4",
    "ふん|分": "N5",
    "キロ|キロ": "N5",
    "せっけん|石鹸": "N5",
    "せっけん|石鹸[けん]": "N5",
    "さらいげつ|再来月": "N4",
    "さらいねん|再来年": "N4",
    "まんなか|真ん中": "N4",
    "つくる|造る": "N3",
}


def load_core_deck_levels() -> dict[str, str]:
    text = base.fetch_text(base.URLS["core"])
    return {r["key"]: r["level"] for r in exact.parse_core_records(text)}


def clean_display(display: str) -> str:
    """Normalize only mechanical display artefacts, not lexical variants."""
    s = v1.norm(display)
    # Core source occasionally embeds bracketed kana as furigana in the written form.
    s = re.sub(r"[\[［][ぁ-ゖァ-ヺー・ヽヾゝゞ]+[\]］]", "", s)
    return s


def normalized_key(key: str) -> str:
    reading, sep, display = key.partition("|")
    if not sep:
        return key
    return f"{v1.norm(reading)}|{clean_display(display)}"


def build_normalized_unique(mapping: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for key, values in mapping.items():
        if isinstance(values, str):
            vals = {values}
        else:
            vals = {x for x in (values or set()) if x in VALID}
        nk = normalized_key(str(key))
        if vals:
            out.setdefault(nk, set()).update(vals)
    return out


def unique(mapping: dict, key: str) -> str:
    values = mapping.get(key) or set()
    if isinstance(values, str):
        return values if values in VALID else ""
    values = {x for x in values if x in VALID}
    return next(iter(values)) if len(values) == 1 else ""


def direct_existing(row: dict) -> str:
    source = str(row.get("level_source") or "")
    level = str(row.get("level") or "")
    return level if level in VALID and not v1.estimated_source(source) else ""


def evidence_for(row: dict, *, manual: dict, core_deck: dict, open_key: dict,
                 waller_key: dict, waller_id: dict, norm_core: dict,
                 norm_open: dict, norm_waller: dict) -> dict[str, str]:
    key = row["key"]
    nk = normalized_key(key)
    out: dict[str, str] = {}
    if key in TEACHER_ANCHORS:
        out["teacher-anchor"] = TEACHER_ANCHORS[key]
    if key in manual:
        out["manual-secondary-exact"] = manual[key]
    if key in core_deck:
        out["core-deck-exact"] = core_deck[key]
    o = unique(open_key, key)
    if o:
        out["openjlpt-exact"] = o
    w = unique(waller_key, key)
    if w:
        out["waller-exact"] = w
    cur = direct_existing(row)
    if cur:
        out["existing-direct"] = cur
    # Mechanical-normalization evidence is useful only when the written key changes.
    if nk != key:
        c = unique(norm_core, nk)
        o2 = unique(norm_open, nk)
        w2 = unique(norm_waller, nk)
        if c:
            out["core-deck-normalized"] = c
        if o2:
            out["openjlpt-normalized"] = o2
        if w2:
            out["waller-normalized"] = w2
    # Entry-level Waller is deliberately context-only. Different forms/senses in one
    # JMdict entry can have different pedagogical difficulty.
    eid = str(row.get("entry_id") or "")
    wid = unique(waller_id, eid) if eid else ""
    if wid:
        out["waller-entry-context"] = wid
    return out


def exact_values(ev: dict[str, str]) -> list[str]:
    keys = (
        "core-deck-exact", "openjlpt-exact", "waller-exact", "existing-direct",
        "core-deck-normalized", "openjlpt-normalized", "waller-normalized",
    )
    return [ev[k] for k in keys if ev.get(k) in VALID]


def level_span(levels: list[str]) -> int:
    xs = [IDX[x] for x in levels if x in VALID]
    return (max(xs) - min(xs)) if xs else 0


def choose_direct(row: dict, ev: dict[str, str]) -> tuple[str, str, str, bool]:
    """Return level, grade(A-C), basis, conflict. Empty level means estimate."""
    key = row["key"]
    if key in TEACHER_ANCHORS:
        return TEACHER_ANCHORS[key], "A", "teacher-anchor", False
    if ev.get("manual-secondary-exact"):
        return ev["manual-secondary-exact"], "A", "manual-secondary-exact", False

    core = ev.get("core-deck-exact", "")
    op = ev.get("openjlpt-exact", "")
    wa = ev.get("waller-exact", "")
    cur = ev.get("existing-direct", "")
    norm_labels = [ev.get(k, "") for k in ("core-deck-normalized", "openjlpt-normalized", "waller-normalized") if ev.get(k)]
    vals = exact_values(ev)
    conflict = len(set(vals)) > 1

    # The core exact key is the pedagogical baseline. Same-entry evidence never beats it.
    if core:
        external = [x for x in (op, wa) if x]
        # Two independent exact lists agreeing can make a one-level correction.
        if op and wa and op == wa and op != core and abs(IDX[op] - IDX[core]) <= 1:
            return op, "A", "two-exact-sources-over-core-adjacent", True
        # For a large disagreement on common/basic core vocabulary, do not manufacture
        # an advanced label. Keep the core level and expose the conflict for review.
        if external and any(abs(IDX[x] - IDX[core]) >= 2 for x in external):
            return core, "C", "core-exact-large-conflict-kept", True
        if core in external or not external:
            return core, "A" if core in external else "B", "core-exact-corroborated" if core in external else "core-exact", conflict
        # Adjacent disagreement without two-source agreement: keep stable core baseline.
        return core, "B", "core-exact-adjacent-conflict-kept", True

    # Non-core exact evidence.
    if op and wa and op == wa:
        return op, "A", "openjlpt+waller-exact", conflict
    if op and wa and op != wa:
        if cur and cur in {op, wa}:
            return cur, "C", "exact-conflict-existing-direct-tiebreak", True
        # For common words, prefer the easier interpretation when exact sources differ
        # by multiple bands; this avoids using N1 as a garbage bucket.
        if row.get("common") and abs(IDX[op] - IDX[wa]) >= 2:
            chosen = min((op, wa), key=lambda x: IDX[x])
            return chosen, "C", "exact-conflict-common-easier", True
        # Otherwise choose the midpoint-nearest label, with easier tie break.
        centre = (IDX[op] + IDX[wa]) / 2.0
        chosen = min((op, wa), key=lambda x: (abs(IDX[x] - centre), IDX[x]))
        return chosen, "C", "exact-conflict-midpoint", True
    if op or wa:
        chosen = op or wa
        if cur and cur != chosen:
            return chosen, "C", "single-exact-over-existing-conflict", True
        return chosen, "B", "single-exact-source", conflict

    # Normalized-equivalent evidence repairs source formatting artefacts only.
    if norm_labels:
        counts = Counter(norm_labels)
        top, n = counts.most_common(1)[0]
        if n >= 2 or len(set(norm_labels)) == 1:
            return top, "B", "mechanically-normalized-exact", len(set(norm_labels)) > 1

    if cur:
        return cur, "B", "existing-direct-exact-row", conflict

    # Entry-level Waller context alone is not safe enough to call a form directly tested.
    return "", "D", "estimate-required", conflict


def model_score(row: dict, model: dict) -> tuple[float, float]:
    _choice, confidence, scores = v1.predict(row, model, None)
    m = max(scores.values())
    ex = {k: math.exp(v - m) for k, v in scores.items()}
    total = sum(ex.values()) or 1.0
    difficulty = sum(IDX[k] * (ex[k] / total) for k in LEVELS)
    rank = row.get("rank")
    if isinstance(rank, int) and rank > 0:
        difficulty += min(math.log10(rank) / 100.0, 0.06)
    return difficulty, confidence


def allocate_estimates(all_rows: list[dict], model: dict, open_counts: dict, n1_floor: float | None):
    estimated = [r for r in all_rows if not r.get("teacher_direct")]
    direct_counts = Counter(r["level"] for r in all_rows if r.get("teacher_direct"))
    for r in estimated:
        r["difficulty"], r["model_confidence"] = model_score(r, model)

    targets = v2.calibrated_targets(len(all_rows), open_counts)
    quotas = v2.residual_quotas(targets, direct_counts, len(estimated))

    min_n1_rank = int(round(10 ** n1_floor)) if n1_floor is not None else 20000
    min_n1_rank = max(min_n1_rank, 10000)
    n1_eligible = [
        r for r in estimated
        if (not r.get("common")) and isinstance(r.get("rank"), int)
        and r["rank"] >= min_n1_rank
    ]
    n1_eligible.sort(key=lambda r: (r["difficulty"], r.get("rank") or 0), reverse=True)
    n1_take = min(quotas["N1"], len(n1_eligible))
    n1_ids = {id(r) for r in n1_eligible[:n1_take]}
    shortfall = quotas["N1"] - n1_take
    quotas["N1"] = n1_take
    if shortfall > 0:
        quotas["N2"] += (shortfall + 1) // 2
        quotas["N3"] += shortfall // 2

    remaining = [r for r in estimated if id(r) not in n1_ids]
    remaining.sort(key=lambda r: (r["difficulty"], r.get("rank") or 0, r["key"]))
    bands = ["N5", "N4", "N3", "N2"]
    quotas["N2"] += len(remaining) - sum(quotas[x] for x in bands)
    pos = 0
    for level in bands:
        take = max(0, quotas[level])
        for r in remaining[pos:pos + take]:
            r["level"] = level
            r["level_source"] = "teacher-v4-calibrated-estimate"
            r["teacher_grade"] = "D"
            r["teacher_basis"] = "model+frequency+world-distribution"
        pos += take
    if pos != len(remaining):
        raise RuntimeError(f"estimate allocation mismatch assigned={pos} remaining={len(remaining)} quotas={quotas}")
    for r in estimated:
        if id(r) in n1_ids:
            r["level"] = "N1"
            r["level_source"] = "teacher-v4-calibrated-estimate"
            r["teacher_grade"] = "D"
            r["teacher_basis"] = "rarity-supported-model+world-distribution"
    return estimated, direct_counts, targets, quotas, min_n1_rank


def write_core(meta: dict, rows: list[dict]):
    tuples = [[
        r["reading"], r["display"], r["level"], r["meaning"], r["meaning_source"],
        r["level_source"], r.get("entry_id"), r.get("teacher_grade", ""), r.get("teacher_basis", "")
    ] for r in rows]
    meta = dict(meta)
    meta.update({
        "version": "core-verified-20260826-v4-teacher-audit",
        "generated": datetime.now(timezone.utc).isoformat(),
        "levelPolicy": "teacher exact-key audit; exact evidence before estimates; same-JMdict variants are context only",
    })
    v1.CORE.write_text(
        "// AUTO-GENERATED teacher-audited JLPT core overlay. Do not edit by hand.\n"
        "(()=>{\"use strict\";\n"
        f"const M={json.dumps(meta,ensure_ascii=False,separators=(',',':'))},T={json.dumps(tuples,ensure_ascii=False,separators=(',',':'))},map=new Map();\n"
        "for(const x of T)map.set(`${x[0]}|${x[1]}`,{level:x[2],meaning:x[3],meaningSource:x[4],levelSource:x[5],entryId:x[6]||null,teacherGrade:x[7]||\"\",teacherBasis:x[8]||\"\"});\n"
        "window.VOCAB_CORE_VERIFIED=map;window.VOCAB_CORE_VERIFIED_META=M;\n"
        "})();\n", encoding="utf-8")


def write_advanced(meta: dict, rows: list[dict], recal: dict):
    counts = Counter(r["level"] for r in rows)
    sources = Counter(r["level_source"] for r in rows)
    tuples = [[
        r["level"], r["reading"], r["kanji"], r["meaning"], r["pos"], r["level_source"],
        r.get("entry_id"), r.get("quality", ""), r.get("model_confidence"),
        r.get("rank") if r.get("rank") and r["rank"] < 999999999 else None,
        r.get("teacher_grade", ""), r.get("teacher_basis", "")
    ] for r in rows]
    meta = dict(meta)
    meta.update({
        "version": "prebuilt-20260826-v9-teacher-audit",
        "generated": datetime.now(timezone.utc).isoformat(),
        "countsByLevel": {x: counts.get(x, 0) for x in ["N1", "N2", "N3", "N4", "N5"]},
        "levelSources": dict(sources),
        "jlptRecalibration": recal,
        "levelPolicy": "teacher exact-key audit first; calibrated estimate only for residual words",
    })
    v1.ADV.write_text(
        "// AUTO-GENERATED teacher-audited JLPT vocabulary. Do not edit by hand.\n"
        "(()=>{\"use strict\";\n" +
        f"const M={json.dumps(meta,ensure_ascii=False,separators=(',',':'))},T={json.dumps(tuples,ensure_ascii=False,separators=(',',':'))};\n" +
        "window.ADVANCED_WORDS=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];const base=window.ADVANCED_WORDS.length;"
        "for(let i=0;i<T.length;i++){const x=T[i];window.ADVANCED_WORDS.push({id:`bundle-${i}`,level:x[0],reading:x[1],kanji:x[2]||\"\",displayWord:x[2]||x[1],meaning:x[3],pos:x[4]||\"other\",estimated:String(x[5]||\"\").includes(\"estimate\"),levelSource:x[5]||\"\",entryId:x[6]||null,qualityTier:x[7]||\"\",jlptConfidence:x[8]??null,frequencyRank:x[9]??null,teacherGrade:x[10]||\"\",teacherBasis:x[11]||\"\",source:\"進階補充詞（日文老師逐詞 JLPT 審核）\"});}"
        "window.ADVANCED_WORDS_BUNDLE_META={...M,loadedCount:window.ADVANCED_WORDS.length-base};window.VOCAB_JLPT_RECALIBRATION_META=M.jlptRecalibration;})();\n",
        encoding="utf-8")


def write_teacher_audit(rows: list[dict]):
    with TEACHER_AUDIT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["reading", "display", "level", "grade", "status", "basis", "common", "frequency_rank", "entry_id", "evidence"])
        for r in sorted(rows, key=lambda x: (IDX.get(x["level"], 99), x["reading"], x["display"])):
            status = "direct" if r.get("teacher_direct") else "estimated"
            if r.get("teacher_conflict"):
                status += "+conflict"
            w.writerow([
                r["reading"], r["display"], r["level"], r.get("teacher_grade", ""), status,
                r.get("teacher_basis", ""), "1" if r.get("common") else "0", r.get("rank") or "",
                r.get("entry_id") or "", json.dumps(r.get("teacher_evidence", {}), ensure_ascii=False, separators=(",", ":")),
            ])


def main() -> int:
    if not v1.DB.exists():
        raise RuntimeError(f"Tomoshi DB missing: {v1.DB}")
    adv_meta, adv_raw = v1.load_bundle()
    core_meta, core_raw = v1.load_core()
    conn = sqlite3.connect(str(v1.DB))
    common, ranks = v1.load_db_evidence(conn)
    waller_id, waller_key = v1.load_waller()
    open_key, open_counts = v1.load_openjlpt()
    manual = v1.load_manual_secondary()
    core_deck = load_core_deck_levels()
    core, advanced = v2.build_rows(common, ranks, adv_raw, core_raw)
    all_rows = core + advanced

    norm_core = build_normalized_unique(core_deck)
    norm_open = build_normalized_unique(open_key)
    norm_waller = build_normalized_unique(waller_key)

    grade_counts = Counter()
    basis_counts = Counter()
    conflicts = []
    for r in all_rows:
        ev = evidence_for(
            r, manual=manual, core_deck=core_deck, open_key=open_key, waller_key=waller_key,
            waller_id=waller_id, norm_core=norm_core, norm_open=norm_open, norm_waller=norm_waller,
        )
        level, grade, basis, conflict = choose_direct(r, ev)
        r["teacher_evidence"] = ev
        r["teacher_conflict"] = bool(conflict)
        if level:
            r["level"] = level
            r["level_source"] = f"teacher-v4-{basis}"
            r["teacher_grade"] = grade
            r["teacher_basis"] = basis
            r["teacher_direct"] = True
            grade_counts[grade] += 1
            basis_counts[basis] += 1
        else:
            r["teacher_direct"] = False
        if conflict:
            conflicts.append({"key": r["key"], "selected": level or None, "grade": grade, "basis": basis, "evidence": ev})

    # Train only on teacher-direct rows, then estimate the residual population.
    for r in all_rows:
        r["direct"] = bool(r.get("teacher_direct"))
    model, train_counts, medians, n1_floor = v1.train_model(all_rows)
    estimated, direct_counts, targets, quotas, min_n1_rank = allocate_estimates(all_rows, model, open_counts, n1_floor)
    grade_counts["D"] += len(estimated)
    basis_counts["estimated"] += len(estimated)

    combined = Counter(r["level"] for r in all_rows)
    exact_keys = Counter(r["key"] for r in all_rows)
    duplicate_keys = [k for k, n in exact_keys.items() if n > 1]
    estimated_n1_without_rarity = [
        r["key"] for r in estimated if r["level"] == "N1" and
        (r.get("common") or not isinstance(r.get("rank"), int) or r["rank"] < min_n1_rank)
    ]
    if duplicate_keys:
        raise RuntimeError(f"duplicate runtime exact keys: {duplicate_keys[:20]}")
    if estimated_n1_without_rarity:
        raise RuntimeError(f"estimated N1 lacks rarity evidence: {estimated_n1_without_rarity[:20]}")

    # Hard teacher sentinels are checked after every decision/estimate.
    sentinel_result = {}
    for key, expected in TEACHER_ANCHORS.items():
        row = next((r for r in all_rows if r["key"] == key), None)
        if row is None:
            # Some anchors are source-format variants and may legitimately be absent.
            if key in {"せっけん|石鹸", "せっけん|石鹸[けん]"}:
                continue
            raise RuntimeError(f"missing teacher sentinel: {key}")
        sentinel_result[key] = {"level": row["level"], "grade": row.get("teacher_grade"), "basis": row.get("teacher_basis")}
        if row["level"] != expected:
            raise RuntimeError(f"teacher sentinel failed {key}: expected {expected}, got {row['level']}")

    write_teacher_audit(all_rows)
    recal = {
        "status": "complete",
        "version": "20260826-teacher-v4-exact-audit",
        "scope": "every core+advanced runtime word exact key",
        "rowCount": len(all_rows),
        "policy": "Teacher audit per exact reading+display key. Manual/teacher anchors first; core exact baseline and exact OpenJLPT/Waller evidence next; same-JMdict-form evidence never decides a level; only residual words are model/distribution estimates; estimated N1 requires positive rarity evidence.",
        "sources": [
            "original 5mdld N1-N5 core deck", "OpenJLPT CC-BY-SA exact entries",
            "Japanese Language Data Waller/Tanos exact entries", "existing Tomoshi/Waller/core exact direct labels",
            "Mazii/MOJi/時雨 targeted exact secondary cross-check layer",
            "Tomoshi/JMdict commonness and frequency for residual estimation only",
        ],
        "combinedCountsByLevel": {x: combined.get(x, 0) for x in LEVELS},
        "directCountsByLevel": dict(direct_counts),
        "estimatedCountsByLevel": dict(Counter(r["level"] for r in estimated)),
        "teacherGradeCounts": dict(grade_counts),
        "teacherBasisCounts": dict(basis_counts),
        "directRows": sum(1 for r in all_rows if r.get("teacher_direct")),
        "estimatedRows": len(estimated),
        "directConflictRows": len(conflicts),
        "directConflictSamples": conflicts[:200],
        "coreDeckExactEvidence": len(core_deck),
        "manualSecondaryExactConfigured": len(manual),
        "trainingCountsByLevel": dict(train_counts),
        "worldTargetCounts": targets,
        "residualQuotas": quotas,
        "modelRankLogMedians": medians,
        "estimatedN1MinimumFrequencyRank": min_n1_rank,
        "estimatedN1WithoutRarityEvidence": len(estimated_n1_without_rarity),
        "duplicateExactKeys": len(duplicate_keys),
        "teacherSentinels": sentinel_result,
        "auditArtifact": "data/jlpt_teacher_audit.tsv",
        "officialJlptCaveat": "JLPT does not publish a canonical post-2010 word-by-word vocabulary list; non-direct rows are teacher-style study estimates, not official JLPT classifications.",
    }
    write_core(core_meta, core)
    write_advanced(adv_meta, advanced, recal)
    audit = json.loads(v1.AUDIT.read_text(encoding="utf-8"))
    audit["jlptRecalibration"] = recal
    audit.setdefault("counts", {})["jlptCountsCoreAdvanced"] = {x: combined.get(x, 0) for x in ["N1", "N2", "N3", "N4", "N5"]}
    audit.setdefault("policy", {})["jlptLevel"] = recal["policy"]
    v1.AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(recal, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
