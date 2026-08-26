#!/usr/bin/env python3
"""World-evidence JLPT recalibration v2.

Direct exact/community labels are fixed first. Residual unlabeled rows are ordered by
a feature model trained on directly labelled runtime words, then allocated across N5-N1
using the published Waller/OpenJLPT vocabulary proportions as a calibration prior.
Estimated N1 requires an observed frequency rank; missing frequency can never create N1.
"""
from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter
from pathlib import Path

import recalibrate_jlpt_world as v1

# Japanese Language Data metadata (Waller/Tanos vocabulary counts).
WALLER_COUNTS = {"N5": 684, "N4": 640, "N3": 1730, "N2": 1812, "N1": 3427}
LEVELS = v1.LEVELS
VALID = v1.VALID


def softmax_expected(scores: dict[str, float]) -> float:
    m = max(scores.values())
    ex = {k: math.exp(v - m) for k, v in scores.items()}
    total = sum(ex.values()) or 1.0
    return sum(LEVELS.index(k) * (ex[k] / total) for k in LEVELS)


def model_score(row: dict, model: dict) -> tuple[float, float]:
    # Reuse v1's calibrated likelihood model. The chosen class itself is not used here;
    # we use the full posterior ordering as a continuous difficulty score.
    _choice, confidence, scores = v1.predict(row, model, None)
    difficulty = softmax_expected(scores)
    # Tie-break using observed frequency: larger rank = harder. Missing rank is neutral,
    # never automatically advanced.
    rank = row.get("rank")
    if isinstance(rank, int) and rank > 0:
        difficulty += min(math.log10(rank) / 100.0, 0.06)
    return difficulty, confidence


def calibrated_targets(total: int, open_counts: dict[str, int]) -> dict[str, int]:
    # Average the two maintained/community datasets instead of privileging one list.
    combined = {lvl: (WALLER_COUNTS[lvl] + int(open_counts.get(lvl, 0))) / 2.0 for lvl in LEVELS}
    denom = sum(combined.values()) or 1.0
    targets = {lvl: int(round(total * combined[lvl] / denom)) for lvl in LEVELS}
    # Force exact total after rounding; N1 is the largest bucket in both source datasets.
    targets["N1"] += total - sum(targets.values())
    return targets


def residual_quotas(targets: dict[str, int], direct: Counter, estimated_total: int) -> dict[str, int]:
    raw = {lvl: max(0, targets[lvl] - direct[lvl]) for lvl in LEVELS}
    s = sum(raw.values())
    if s == estimated_total:
        return raw
    if s <= 0:
        # Defensive fallback: distribute by world target proportions.
        s = sum(targets.values())
        raw = {lvl: int(round(estimated_total * targets[lvl] / s)) for lvl in LEVELS}
    else:
        scaled = {lvl: int(round(estimated_total * raw[lvl] / s)) for lvl in LEVELS}
        raw = scaled
    diff = estimated_total - sum(raw.values())
    # Adjust in the middle/upper bands first; never manufacture extra N5 by rounding.
    order = ["N2", "N3", "N1", "N4", "N5"]
    i = 0
    while diff != 0:
        lvl = order[i % len(order)]
        if diff > 0:
            raw[lvl] += 1
            diff -= 1
        elif raw[lvl] > 0:
            raw[lvl] -= 1
            diff += 1
        i += 1
    return raw


def build_rows(common: dict, ranks: dict, adv_raw: list, core_raw: list):
    advanced = []
    for x in adv_raw:
        if not isinstance(x, list) or len(x) < 7:
            continue
        level, reading, kanji, meaning, pos, source, eid = x[:7]
        display = str(kanji or reading)
        eid = str(eid or "") or None
        advanced.append({
            "kind":"advanced","level":str(level),"reading":str(reading),"kanji":str(kanji or ""),"display":display,
            "meaning":str(meaning),"pos":str(pos or "other"),"level_source":str(source or ""),"entry_id":eid,
            "quality":str(x[7] or "") if len(x)>7 else "","key":f"{reading}|{display}",
            "rank":ranks.get(eid) if eid else None,"common":bool(common.get(eid,False)) if eid else False,
        })
    core = []
    for x in core_raw:
        if not isinstance(x, list) or len(x) < 7:
            continue
        reading, display, level, meaning, meaning_source, level_source, eid = x[:7]
        eid = str(eid or "") or None
        core.append({
            "kind":"core","level":str(level),"reading":str(reading),"display":str(display),"meaning":str(meaning),
            "meaning_source":str(meaning_source),"level_source":str(level_source),"entry_id":eid,
            "key":f"{reading}|{display}","rank":ranks.get(eid) if eid else None,
            "common":bool(common.get(eid,False)) if eid else False,
        })
    return core, advanced


def main():
    if not v1.DB.exists():
        raise RuntimeError(f"Tomoshi DB missing: {v1.DB}")
    adv_meta, adv_raw = v1.load_bundle()
    core_meta, core_raw = v1.load_core()
    conn = sqlite3.connect(str(v1.DB))
    common, ranks = v1.load_db_evidence(conn)
    waller_id, waller_key = v1.load_waller()
    open_key, open_counts = v1.load_openjlpt()
    manual = v1.load_manual_secondary()
    core, advanced = build_rows(common, ranks, adv_raw, core_raw)

    conflicts1, added1 = v1.apply_world_evidence(core, waller_id, waller_key, open_key, manual)
    conflicts2, added2 = v1.apply_world_evidence(advanced, waller_id, waller_key, open_key, manual)
    all_rows = core + advanced
    model, train_counts, medians, n1_floor = v1.train_model(all_rows)

    estimated = [r for r in all_rows if not r.get("direct")]
    direct = Counter(r["level"] for r in all_rows if r.get("direct"))
    for r in estimated:
        r["difficulty"], r["confidence"] = model_score(r, model)

    targets = calibrated_targets(len(all_rows), open_counts)
    quotas = residual_quotas(targets, direct, len(estimated))

    # N1 is assigned only among the hardest estimated rows that have positive frequency evidence.
    n1_eligible = [r for r in estimated if isinstance(r.get("rank"), int) and r["rank"] > 0]
    n1_eligible.sort(key=lambda r: (r["difficulty"], r.get("rank") or 0), reverse=True)
    n1_take = min(quotas["N1"], len(n1_eligible))
    n1_ids = {id(r) for r in n1_eligible[:n1_take]}
    quotas["N1"] = n1_take
    leftovers_from_n1 = max(0, len(estimated) - (sum(quotas[l] for l in LEVELS)))
    # Any N1 quota that could not be supported by observed frequency is redistributed to N2/N3.
    if leftovers_from_n1:
        n2_add = (leftovers_from_n1 + 1) // 2
        quotas["N2"] += n2_add
        quotas["N3"] += leftovers_from_n1 - n2_add

    remaining = [r for r in estimated if id(r) not in n1_ids]
    remaining.sort(key=lambda r: (r["difficulty"], r.get("rank") or 0, r["key"]))
    non_n1_levels = ["N5", "N4", "N3", "N2"]
    expected_non_n1 = len(remaining)
    non_n1_quota = sum(quotas[l] for l in non_n1_levels)
    if non_n1_quota != expected_non_n1:
        quotas["N2"] += expected_non_n1 - non_n1_quota
    pos = 0
    for lvl in non_n1_levels:
        take = max(0, quotas[lvl])
        for r in remaining[pos:pos+take]:
            r["level"] = lvl
            r["level_source"] = "world-distribution-calibrated-estimate"
        pos += take
    if pos != len(remaining):
        raise RuntimeError(f"residual allocation mismatch: assigned={pos} remaining={len(remaining)} quotas={quotas}")
    for r in estimated:
        if id(r) in n1_ids:
            r["level"] = "N1"
            r["level_source"] = "world-distribution-calibrated-estimate"

    combined = Counter(r["level"] for r in all_rows)
    estimated_counts = Counter(r["level"] for r in estimated)
    n1_without_rank = sum(1 for r in estimated if r["level"] == "N1" and not r.get("rank"))
    if n1_without_rank:
        raise RuntimeError(f"estimated N1 without observed frequency: {n1_without_rank}")
    # World-prior calibration should be close to the published proportions, allowing
    # direct-evidence constraints to move the final totals modestly.
    if combined["N1"] >= 14500:
        raise RuntimeError(f"N1 still implausibly inflated after calibrated allocation: {combined}")
    if combined["N5"] < 1500 or combined["N4"] < 1500 or combined["N3"] < 4000:
        raise RuntimeError(f"lower/intermediate bands still implausibly thin: {combined}")
    suika = next((r for r in all_rows if r["key"] == "すいか|西瓜"), None)
    if not suika or suika["level"] != "N5":
        raise RuntimeError(f"西瓜 sentinel failed: {suika}")

    recal = {
        "status":"complete",
        "version":"20260826-world-v2-distribution-calibrated",
        "sources":["existing core/Waller/Tomoshi direct labels","Japanese Language Data Waller/Tanos CC-BY-SA","OpenJLPT CC-BY-SA","Mazii/MOJi/時雨 exact manual secondary cross-check layer","Tomoshi/JMdict frequency/commonness for residual difficulty features"],
        "policy":"Direct evidence is fixed first. Residual words are difficulty-ranked by a model trained on direct labels, then distribution-calibrated to the average Waller/OpenJLPT level proportions. Missing frequency never implies N1; estimated N1 requires observed frequency.",
        "trainingDirectRows":sum(train_counts.values()),
        "trainingCountsByLevel":dict(train_counts),
        "directCountsByLevel":dict(direct),
        "estimatedCountsByLevel":dict(estimated_counts),
        "combinedCountsByLevel":dict(combined),
        "worldTargetCounts":targets,
        "residualQuotas":quotas,
        "newDirectEvidence":dict(added1 + added2),
        "wallerPublishedCounts":WALLER_COUNTS,
        "openJlptPublishedCounts":open_counts,
        "modelRankLogMedians":medians,
        "modelN1RankLogFloor":n1_floor,
        "estimatedN1WithoutObservedRank":n1_without_rank,
        "worldEvidenceConflictCount":len(conflicts1)+len(conflicts2),
        "worldEvidenceConflictSamples":(conflicts1+conflicts2)[:100],
        "manualSecondaryExactConfigured":len(manual),
    }
    v1.write_core(core_meta, core)
    v1.write_advanced(adv_meta, advanced, recal)
    audit = json.loads(v1.AUDIT.read_text(encoding="utf-8"))
    audit["jlptRecalibration"] = recal
    audit.setdefault("counts", {})["jlptCountsCoreAdvanced"] = {x: combined.get(x, 0) for x in ["N1","N2","N3","N4","N5"]}
    audit.setdefault("policy", {})["jlptLevel"] = recal["policy"]
    v1.AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(recal, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
