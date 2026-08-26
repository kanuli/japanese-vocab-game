#!/usr/bin/env python3
"""World-evidence JLPT recalibration v3: per-word consensus first, model second.

The previous distribution calibration fixed the N1 garbage-bucket problem, but a final
conflict audit exposed individual common words where one community list disagreed with
other well-known learning evidence. This pass therefore resolves EACH directly-covered
word from weighted evidence before estimating the residual population.

Evidence order/policy:
  * exact manual secondary validation (Mazii/MOJi/時雨 layer): hard override;
  * original 5mdld N1-N5 core deck exact key: strong vote;
  * OpenJLPT exact form+reading: strong vote;
  * OpenJLPT evidence on another form of the SAME JMdict entry: supporting vote;
  * existing Waller/Tomoshi/core direct label: supporting vote;
  * Japanese Language Data Waller/Tanos exact/entry evidence: supporting vote when it
    is not merely duplicating the current Waller-labelled source.

Only rows without decisive direct evidence are estimated. Residual estimates are still
calibrated to the world/community level proportions, and an estimated N1 requires an
observed frequency rank. Missing frequency is never N1 evidence.
"""
from __future__ import annotations

import json
import math
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone

import build_vocab_bundle as base
import build_vocab_bundle_exact as exact
import recalibrate_jlpt_world as v1
import recalibrate_jlpt_world_v2 as v2

LEVELS = v1.LEVELS
VALID = v1.VALID
IDX = {level: i for i, level in enumerate(LEVELS)}  # N5 easiest -> N1 hardest


def load_core_deck_levels() -> dict[str, str]:
    text = base.fetch_text(base.URLS["core"])
    return {r["key"]: r["level"] for r in exact.parse_core_records(text)}


def load_entry_forms(conn: sqlite3.Connection) -> dict[str, tuple[str, ...]]:
    out = {}
    for eid, raw in conn.execute("SELECT id, data FROM entries"):
        try:
            data = json.loads(raw or "{}")
        except Exception:
            continue
        forms = []
        for group in (data.get("kanji") or [], data.get("kana") or []):
            for x in group:
                if not isinstance(x, dict):
                    continue
                text = v1.norm(x.get("text"))
                if text and text not in forms:
                    forms.append(text)
        out[str(eid)] = tuple(forms)
    return out


def unique_label(mapping: dict, key: str) -> str:
    return v1.unique(mapping, key)


def open_variant_evidence(row: dict, entry_forms: dict, open_key: dict) -> set[str]:
    eid = str(row.get("entry_id") or "")
    reading = v1.norm(row.get("reading"))
    if not eid or not reading:
        return set()
    labels = set()
    for form in entry_forms.get(eid, ()):  # same JMdict lexical entry only
        labels.update(open_key.get(f"{reading}|{form}") or set())
        if v1.KANA_RE.fullmatch(form):
            labels.update(open_key.get(f"{form}|{form}") or set())
    return {x for x in labels if x in VALID}


def current_direct_weight(source: str) -> int:
    s = str(source or "").lower()
    if v1.estimated_source(s):
        return 0
    if "manual-secondary" in s or "curated-exact" in s:
        return 8
    if "core-deck" in s:
        return 4
    if "waller" in s:
        return 3
    if "tomoshi" in s:
        return 3
    return 2


def choose_weighted(votes: list[tuple[str, int, str]], common: bool) -> tuple[str, dict, int, int]:
    score = Counter()
    sources = defaultdict(list)
    for level, weight, source in votes:
        if level not in VALID or weight <= 0:
            continue
        score[level] += weight
        sources[level].append(source)
    if not score:
        return "", {}, 0, 0
    best_weight = max(score.values())
    best = [x for x in LEVELS if score[x] == best_weight]
    if len(best) == 1:
        chosen = best[0]
    else:
        # Tie: choose closest to the weighted evidence centre. For a still-exact tie,
        # favour the easier label for common vocabulary rather than manufacturing N1.
        total_w = sum(score.values())
        centre = sum(IDX[lvl] * w for lvl, w in score.items()) / max(total_w, 1)
        best.sort(key=lambda lvl: (abs(IDX[lvl] - centre), IDX[lvl] if common else -IDX[lvl]))
        chosen = best[0]
    ordered_weights = sorted(score.values(), reverse=True)
    margin = ordered_weights[0] - (ordered_weights[1] if len(ordered_weights) > 1 else 0)
    detail = {lvl: {"weight": score[lvl], "sources": sources[lvl]} for lvl in LEVELS if score[lvl]}
    return chosen, detail, best_weight, margin


def apply_consensus(rows: list[dict], *, manual: dict, core_deck: dict, open_key: dict,
                    waller_id: dict, waller_key: dict, entry_forms: dict):
    conflicts = []
    overrides = []
    source_use = Counter()
    for r in rows:
        key = r["key"]
        old_level = r.get("level")
        old_source = str(r.get("level_source") or "")
        if key in manual:
            r["level"] = manual[key]
            r["level_source"] = "manual-secondary-crosscheck-exact"
            r["direct"] = True
            r["consensus_detail"] = {manual[key]: {"weight": 100, "sources": ["manual-secondary-exact"]}}
            source_use["manual-secondary-exact"] += 1
            if old_level != r["level"]:
                overrides.append({"key": key, "from": old_level, "to": r["level"], "reason": "manual-secondary-exact"})
            continue

        votes: list[tuple[str, int, str]] = []
        if key in core_deck:
            votes.append((core_deck[key], 6, "original-core-deck"))
        open_exact = unique_label(open_key, key)
        if open_exact:
            votes.append((open_exact, 5, "openjlpt-exact"))
        variant_labels = open_variant_evidence(r, entry_forms, open_key)
        if len(variant_labels) == 1:
            variant = next(iter(variant_labels))
            # Do not double-count an identical exact OpenJLPT vote at full strength;
            # it still supplies a small same-entry corroboration.
            votes.append((variant, 2 if variant == open_exact else 3, "openjlpt-same-jmdict-entry"))
        elif len(variant_labels) > 1:
            for variant in sorted(variant_labels, key=lambda x: IDX[x]):
                votes.append((variant, 1, "openjlpt-entry-conflict"))

        cw = current_direct_weight(old_source)
        if cw:
            votes.append((old_level, cw, f"existing:{old_source}"))

        # Japanese Language Data Waller/Tanos evidence can add coverage, but avoid
        # counting it twice when the current direct label is already Waller-derived.
        if "waller" not in old_source.lower():
            w = unique_label(waller_id, str(r.get("entry_id") or "")) or unique_label(waller_key, key)
            if w:
                votes.append((w, 2, "waller-tanos-open-data"))

        chosen, detail, best_weight, margin = choose_weighted(votes, bool(r.get("common")))
        distinct = [lvl for lvl, d in detail.items() if d["weight"] > 0]
        if len(distinct) > 1:
            conflicts.append({"key": key, "before": old_level, "beforeSource": old_source, "chosen": chosen, "evidence": detail})
        if chosen and best_weight >= 4:
            r["level"] = chosen
            r["level_source"] = "world-weighted-consensus"
            r["direct"] = True
            r["consensus_detail"] = detail
            source_use["weighted-consensus"] += 1
            if old_level != chosen:
                overrides.append({"key": key, "from": old_level, "to": chosen, "reason": detail})
        else:
            r["direct"] = False
            r["consensus_detail"] = detail
    return conflicts, overrides, source_use


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


def allocate_residual(all_rows: list[dict], model: dict, open_counts: dict):
    estimated = [r for r in all_rows if not r.get("direct")]
    direct_counts = Counter(r["level"] for r in all_rows if r.get("direct"))
    for r in estimated:
        r["difficulty"], r["confidence"] = model_score(r, model)

    targets = v2.calibrated_targets(len(all_rows), open_counts)
    quotas = v2.residual_quotas(targets, direct_counts, len(estimated))

    n1_eligible = [r for r in estimated if isinstance(r.get("rank"), int) and r["rank"] > 0]
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
    non_n1 = ["N5", "N4", "N3", "N2"]
    diff = len(remaining) - sum(quotas[l] for l in non_n1)
    quotas["N2"] += diff
    pos = 0
    for lvl in non_n1:
        take = max(0, quotas[lvl])
        for r in remaining[pos:pos + take]:
            r["level"] = lvl
            r["level_source"] = "world-consensus-distribution-estimate"
        pos += take
    if pos != len(remaining):
        raise RuntimeError(f"residual allocation mismatch: assigned={pos}, remaining={len(remaining)}, quotas={quotas}")
    for r in estimated:
        if id(r) in n1_ids:
            r["level"] = "N1"
            r["level_source"] = "world-consensus-distribution-estimate"
    return estimated, direct_counts, targets, quotas


def write_core(meta: dict, rows: list[dict]):
    tuples = [[r["reading"], r["display"], r["level"], r["meaning"], r["meaning_source"], r["level_source"], r.get("entry_id")] for r in rows]
    meta = dict(meta)
    meta.update({
        "version": "core-verified-20260826-v3-world-consensus",
        "generated": datetime.now(timezone.utc).isoformat(),
        "levelPolicy": "manual exact > weighted per-word world evidence (original core/OpenJLPT/same-JMdict/Waller/Tomoshi) > calibrated residual estimate",
    })
    v1.CORE.write_text(
        "// AUTO-GENERATED weighted-consensus JLPT core overlay. Do not edit by hand.\n"
        "(()=>{\"use strict\";\n"
        f"const M={json.dumps(meta,ensure_ascii=False,separators=(',',':'))},T={json.dumps(tuples,ensure_ascii=False,separators=(',',':'))},map=new Map();\n"
        "for(const x of T)map.set(`${x[0]}|${x[1]}`,{level:x[2],meaning:x[3],meaningSource:x[4],levelSource:x[5],entryId:x[6]||null});\n"
        "window.VOCAB_CORE_VERIFIED=map;window.VOCAB_CORE_VERIFIED_META=M;\n"
        "})();\n", encoding="utf-8")


def write_advanced(meta: dict, rows: list[dict], recal: dict):
    counts = Counter(r["level"] for r in rows)
    sources = Counter(r["level_source"] for r in rows)
    tuples = [[r["level"], r["reading"], r["kanji"], r["meaning"], r["pos"], r["level_source"], r.get("entry_id"), r.get("quality", ""), r.get("confidence"), r.get("rank") if r.get("rank") and r["rank"] < 999999999 else None] for r in rows]
    meta = dict(meta)
    meta.update({
        "version": "prebuilt-20260826-v8-world-consensus",
        "generated": datetime.now(timezone.utc).isoformat(),
        "countsByLevel": {x: counts.get(x, 0) for x in ["N1","N2","N3","N4","N5"]},
        "levelSources": dict(sources),
        "jlptRecalibration": recal,
        "levelPolicy": "per-word weighted world evidence first; residual estimates distribution-calibrated; missing frequency never implies N1",
    })
    v1.ADV.write_text(
        "// AUTO-GENERATED weighted-consensus world JLPT recalibration. Do not edit by hand.\n"
        "(()=>{\"use strict\";\n" + f"const M={json.dumps(meta,ensure_ascii=False,separators=(',',':'))},T={json.dumps(tuples,ensure_ascii=False,separators=(',',':'))};\n" +
        "window.ADVANCED_WORDS=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];const base=window.ADVANCED_WORDS.length;"
        "for(let i=0;i<T.length;i++){const x=T[i];window.ADVANCED_WORDS.push({id:`bundle-${i}`,level:x[0],reading:x[1],kanji:x[2]||\"\",displayWord:x[2]||x[1],meaning:x[3],pos:x[4]||\"other\",estimated:String(x[5]||\"\").includes(\"estimate\"),levelSource:x[5]||\"\",entryId:x[6]||null,qualityTier:x[7]||\"\",jlptConfidence:x[8]??null,frequencyRank:x[9]??null,source:\"進階補充詞（世界 JLPT 多來源逐詞校準）\"});}"
        "window.ADVANCED_WORDS_BUNDLE_META={...M,loadedCount:window.ADVANCED_WORDS.length-base};window.VOCAB_JLPT_RECALIBRATION_META=M.jlptRecalibration;})();\n",
        encoding="utf-8")


def main():
    if not v1.DB.exists():
        raise RuntimeError(f"Tomoshi DB missing: {v1.DB}")
    adv_meta, adv_raw = v1.load_bundle()
    core_meta, core_raw = v1.load_core()
    conn = sqlite3.connect(str(v1.DB))
    common, ranks = v1.load_db_evidence(conn)
    entry_forms = load_entry_forms(conn)
    waller_id, waller_key = v1.load_waller()
    open_key, open_counts = v1.load_openjlpt()
    manual = v1.load_manual_secondary()
    core_deck = load_core_deck_levels()
    core, advanced = v2.build_rows(common, ranks, adv_raw, core_raw)
    all_rows = core + advanced

    conflicts, overrides, source_use = apply_consensus(
        all_rows, manual=manual, core_deck=core_deck, open_key=open_key,
        waller_id=waller_id, waller_key=waller_key, entry_forms=entry_forms)
    model, train_counts, medians, n1_floor = v1.train_model(all_rows)
    estimated, direct_counts, targets, quotas = allocate_residual(all_rows, model, open_counts)

    combined = Counter(r["level"] for r in all_rows)
    estimated_counts = Counter(r["level"] for r in estimated)
    n1_without_rank = sum(1 for r in estimated if r["level"] == "N1" and not r.get("rank"))
    if n1_without_rank:
        raise RuntimeError(f"estimated N1 without observed rank: {n1_without_rank}")
    if combined["N1"] >= 14500:
        raise RuntimeError(f"N1 still implausibly inflated: {combined}")
    if combined["N5"] < 1800 or combined["N4"] < 1500 or combined["N3"] < 4000:
        raise RuntimeError(f"lower/intermediate bands too thin: {combined}")

    required = {
        "すいか|西瓜":"N5", "これ|これ":"N5", "それ|それ":"N5",
        "おもしろい|面白い":"N5", "あかるい|明るい":"N5",
        "おわる|終わる":"N5", "べんきょう|勉強":"N5",
        "さんぽ|散歩":"N5", "だんだん|だんだん":"N5", "もし|もし":"N4",
    }
    sentinels = {}
    for key, expected in required.items():
        row = next((r for r in all_rows if r["key"] == key), None)
        sentinels[key] = None if row is None else {"level":row["level"],"source":row["level_source"]}
        if row is None or row["level"] != expected:
            raise RuntimeError(f"world-knowledge sentinel failed {key}: expected {expected}, got {row}")

    recal = {
        "status":"complete",
        "version":"20260826-world-v3-weighted-consensus",
        "sources":["original 5mdld N1-N5 core deck","existing Waller/Tomoshi direct labels","Japanese Language Data Waller/Tanos CC-BY-SA","OpenJLPT CC-BY-SA exact and same-JMdict-form evidence","Mazii/MOJi/時雨 targeted exact secondary cross-check layer","Tomoshi/JMdict frequency/commonness only for residual model features"],
        "policy":"Resolve each directly-covered word by weighted evidence before any global modelling. Exact manual checks override. Original core and OpenJLPT exact evidence are strong votes; same-JMdict forms and Waller/Tomoshi are supporting votes. Only residual rows are distribution-calibrated. Missing frequency never implies N1.",
        "trainingDirectRows":sum(train_counts.values()),
        "trainingCountsByLevel":dict(train_counts),
        "directCountsByLevel":dict(direct_counts),
        "estimatedCountsByLevel":dict(estimated_counts),
        "combinedCountsByLevel":dict(combined),
        "worldTargetCounts":targets,
        "residualQuotas":quotas,
        "weightedEvidenceConflictCount":len(conflicts),
        "weightedEvidenceConflictSamples":conflicts[:100],
        "existingDirectLevelsOverridden":len(overrides),
        "overrideSamples":overrides[:100],
        "evidenceUse":dict(source_use),
        "manualSecondaryExactConfigured":len(manual),
        "coreDeckExactEvidence":len(core_deck),
        "modelRankLogMedians":medians,
        "modelN1RankLogFloor":n1_floor,
        "estimatedN1WithoutObservedRank":n1_without_rank,
        "worldKnowledgeSentinels":sentinels,
        "wallerPublishedCounts":v2.WALLER_COUNTS,
        "openJlptPublishedCounts":open_counts,
    }
    write_core(core_meta, core)
    write_advanced(adv_meta, advanced, recal)
    audit = json.loads(v1.AUDIT.read_text(encoding="utf-8"))
    audit["jlptRecalibration"] = recal
    audit.setdefault("counts", {})["jlptCountsCoreAdvanced"] = {x: combined.get(x, 0) for x in ["N1","N2","N3","N4","N5"]}
    audit.setdefault("policy", {})["jlptLevel"] = recal["policy"]
    v1.AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(recal, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
