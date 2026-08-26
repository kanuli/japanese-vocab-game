#!/usr/bin/env python3
"""Recalibrate N5-N1 labels from multiple world/community evidence sources.

This runs after the audited Tomoshi/JMdict expansion. It does NOT scrape proprietary
web dictionaries. Direct reusable evidence comes from:
  - existing Waller/Tomoshi/core labels already embedded in the generated data,
  - Japanese Language Data's CC-BY-SA Waller/Tanos classifications,
  - OpenJLPT's CC-BY-SA vocabulary lists,
  - exact manual secondary cross-checks already recorded in this repository
    (Mazii / MOJi / 時雨 validation layer).

Residual rows without a direct JLPT label are estimated with a small Gaussian naive
Bayes model calibrated on the known-labelled runtime population. Missing frequency is
never treated as N1 evidence, and an estimated N1 requires an observed frequency rank.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import statistics
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADV = ROOT / "data" / "advanced_vocab.js"
CORE = ROOT / "data" / "vocab_core_verified.js"
AUDIT = ROOT / "data" / "vocab_audit.json"
EXTERNAL = ROOT / "data" / "vocab_external_crosscheck.js"
DB = Path(os.environ.get("TOMOSHI_DB", "/tmp/tomoshi.db"))
LEVELS = ["N5", "N4", "N3", "N2", "N1"]
VALID = set(LEVELS)
WALLER_URL = "https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/enrichment/jlpt-classifications.json"
OPENJLPT_URL = "https://raw.githubusercontent.com/evanclan/OpenJLPT/main/data/json/vocab/{level}.json"
KANA_RE = re.compile(r"^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$")
KATA_RE = re.compile(r"^[ァ-ヺー・ヽヾ]+$")
CJK_RE = re.compile(r"[\u3400-\u9fff々〆ヵヶ]")


def norm(value) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().replace(" ", "")


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "japanese-vocab-game-jlpt-recalibrator/1.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def parse_js_pair(path: Path, tail: str):
    text = path.read_text(encoding="utf-8")
    start = text.index("const M=") + len("const M=")
    mid = text.index(",T=", start)
    end = text.index(tail, mid + 3)
    return json.loads(text[start:mid]), json.loads(text[mid + 3:end])


def load_bundle():
    try:
        return parse_js_pair(ADV, ";\nwindow.ADVANCED_WORDS")
    except ValueError:
        return parse_js_pair(ADV, ";window.ADVANCED_WORDS")


def load_core():
    return parse_js_pair(CORE, ",map=new Map();")


def load_db_evidence(conn: sqlite3.Connection):
    common = {str(eid): bool(v) for eid, v in conn.execute("SELECT id, is_common FROM entries")}
    cols = [str(r[1]) for r in conn.execute("PRAGMA table_info(freq_rank)")]
    lower = {c.lower(): i for i, c in enumerate(cols)}
    id_idx = next((lower[x] for x in ("entry_id", "entryid", "id") if x in lower), None)
    rank_idx = next((lower[x] for x in ("rank", "freq_rank", "frequency_rank") if x in lower), None)
    ranks = {}
    if id_idx is not None and rank_idx is not None:
        for row in conn.execute("SELECT * FROM freq_rank"):
            eid = str(row[id_idx] or "").strip()
            try:
                rank = int(row[rank_idx])
            except Exception:
                continue
            if eid and rank > 0:
                ranks[eid] = min(rank, ranks.get(eid, rank))
    return common, ranks


def add_level(mapping: dict, key: str, level: str):
    if key and level in VALID:
        mapping.setdefault(key, set()).add(level)


def unique(mapping: dict, key: str) -> str:
    values = mapping.get(key) or set()
    return next(iter(values)) if len(values) == 1 else ""


def load_waller():
    data = fetch_json(WALLER_URL)
    by_id, by_key = {}, {}
    for x in data.get("classifications") or []:
        if x.get("kind") != "vocab":
            continue
        level = str(x.get("level") or "").upper()
        reading, display = norm(x.get("reading")), norm(x.get("text"))
        eid = str(x.get("jmdict_seq") or "").strip()
        if eid:
            add_level(by_id, eid, level)
        if reading and display:
            add_level(by_key, f"{reading}|{display}", level)
    return by_id, by_key


def split_forms(word: str):
    parts = [norm(x) for x in re.split(r"[/／]", norm(word))]
    return [x for x in parts if x]


def load_openjlpt():
    by_key = {}
    counts = Counter()
    for level in LEVELS:
        rows = fetch_json(OPENJLPT_URL.format(level=level.lower()))
        for x in rows if isinstance(rows, list) else []:
            lvl = str(x.get("level") or level).upper()
            reading = norm(x.get("reading"))
            forms = split_forms(x.get("word"))
            for form in forms:
                rd = reading or (form if KANA_RE.fullmatch(form) else "")
                if rd:
                    add_level(by_key, f"{rd}|{form}", lvl)
                    counts[lvl] += 1
    return by_key, dict(counts)


def load_manual_secondary():
    out = {
        "ほてん|補填": "N2",
        "アップル|アップル": "N5",
        "すいか|西瓜": "N5",
    }
    if EXTERNAL.exists():
        text = EXTERNAL.read_text(encoding="utf-8")
        pat = re.compile(r'\["((?:\\.|[^"\\])*)","((?:\\.|[^"\\])*)","(N[1-5])",')
        for m in pat.finditer(text):
            try:
                reading = json.loads('"' + m.group(1) + '"')
                display = json.loads('"' + m.group(2) + '"')
            except Exception:
                continue
            out[f"{norm(reading)}|{norm(display)}"] = m.group(3)
    return out


def estimated_source(source: str) -> bool:
    s = str(source or "").lower()
    return (not s) or "estimate" in s or "common-entry" in s or "frequency" in s


def row_features(row: dict):
    display = row["display"]
    rank = row.get("rank")
    known_rank = isinstance(rank, int) and 0 < rank < 999999999
    chars = list(display)
    return {
        "logrank": math.log10(rank) if known_rank else None,
        "length": float(min(len(chars), 12)),
        "kanji": float(sum(1 for c in chars if CJK_RE.search(c))),
        "common": 1.0 if row.get("common") else 0.0,
        "kana": 1.0 if KANA_RE.fullmatch(display) else 0.0,
        "katakana": 1.0 if KATA_RE.fullmatch(display) else 0.0,
        "hasrank": 1.0 if known_rank else 0.0,
    }


def train_model(rows: list[dict]):
    direct = [r for r in rows if r.get("direct") and r.get("level") in VALID]
    counts = Counter(r["level"] for r in direct)
    total = sum(counts.values())
    params = {}
    continuous = ("logrank", "length", "kanji")
    binary = ("common", "kana", "katakana", "hasrank")
    for level in LEVELS:
        group = [row_features(r) for r in direct if r["level"] == level]
        p = {"prior": (counts[level] + 1) / (total + len(LEVELS)), "continuous": {}, "binary": {}}
        for name in continuous:
            vals = [x[name] for x in group if x[name] is not None]
            mean = statistics.fmean(vals) if vals else 0.0
            var = statistics.fmean([(v - mean) ** 2 for v in vals]) if len(vals) > 1 else 1.0
            p["continuous"][name] = (mean, max(var, 0.04))
        for name in binary:
            yes = sum(x[name] for x in group)
            p["binary"][name] = (yes + 1.0) / (len(group) + 2.0)
        params[level] = p
    rank_medians = {}
    for level in LEVELS:
        vals = [row_features(r)["logrank"] for r in direct if r["level"] == level and row_features(r)["logrank"] is not None]
        rank_medians[level] = statistics.median(vals) if vals else None
    n1_floor = None
    if rank_medians.get("N2") is not None and rank_medians.get("N1") is not None:
        n1_floor = (rank_medians["N2"] + rank_medians["N1"]) / 2.0
    return params, counts, rank_medians, n1_floor


def predict(row: dict, model: dict, n1_floor: float | None):
    f = row_features(row)
    scores = {}
    for level, p in model.items():
        s = math.log(max(p["prior"], 1e-9))
        for name, (mean, var) in p["continuous"].items():
            value = f[name]
            if value is None:
                continue
            s += -0.5 * math.log(2 * math.pi * var) - ((value - mean) ** 2) / (2 * var)
        for name, prob in p["binary"].items():
            prob = min(max(prob, 1e-6), 1 - 1e-6)
            s += math.log(prob if f[name] >= 0.5 else (1 - prob))
        scores[level] = s
    ordered = sorted(scores, key=scores.get, reverse=True)
    chosen = ordered[0]
    # N1 must have positive rarity evidence when it is only an estimate.
    if chosen == "N1":
        lr = f["logrank"]
        margin = scores[ordered[0]] - scores[ordered[1]] if len(ordered) > 1 else 0.0
        if lr is None or (n1_floor is not None and lr < n1_floor) or margin < 0.20:
            chosen = next(x for x in ordered if x != "N1")
    # Do not infer beginner vocabulary from no-evidence, non-common rows.
    if chosen == "N5" and not row.get("common") and f["logrank"] is None:
        chosen = next((x for x in ordered if x not in {"N5", "N1"}), "N4")
    ordered2 = sorted(scores, key=scores.get, reverse=True)
    confidence = scores[chosen] - max((scores[x] for x in ordered2 if x != chosen), default=scores[chosen])
    return chosen, round(confidence, 4), scores


def apply_world_evidence(rows: list[dict], waller_id: dict, waller_key: dict, open_key: dict, manual: dict):
    conflicts = []
    direct_added = Counter()
    for r in rows:
        key = r["key"]
        current_direct = not estimated_source(r.get("level_source", ""))
        if key in manual:
            r["level"] = manual[key]
            r["level_source"] = "manual-secondary-crosscheck-exact"
            r["direct"] = True
            direct_added["manual-secondary"] += 1
            continue
        w = unique(waller_id, r.get("entry_id") or "") or unique(waller_key, key)
        o = unique(open_key, key)
        evidence = [x for x in (w, o) if x]
        if current_direct:
            r["direct"] = True
            if evidence and any(x != r["level"] for x in evidence):
                conflicts.append({"key": key, "kept": r["level"], "source": r.get("level_source"), "waller": w or None, "openjlpt": o or None})
            continue
        if w and o and w == o:
            r["level"] = w
            r["level_source"] = "world-consensus-waller+openjlpt"
            r["direct"] = True
            direct_added["waller+openjlpt"] += 1
        elif w and not o:
            r["level"] = w
            r["level_source"] = "waller-open-data"
            r["direct"] = True
            direct_added["waller"] += 1
        elif o and not w:
            r["level"] = o
            r["level_source"] = "openjlpt-exact"
            r["direct"] = True
            direct_added["openjlpt"] += 1
        elif w and o and w != o:
            r["direct"] = False
            conflicts.append({"key": key, "keptForModel": r["level"], "waller": w, "openjlpt": o})
        else:
            r["direct"] = False
    return conflicts, direct_added


def write_core(meta: dict, rows: list[dict]):
    tuples = [[r["reading"], r["display"], r["level"], r["meaning"], r["meaning_source"], r["level_source"], r.get("entry_id")] for r in rows]
    meta = dict(meta)
    meta.update({
        "version": "core-verified-20260826-v2-world-jlpt",
        "generated": datetime.now(timezone.utc).isoformat(),
        "levelPolicy": "exact manual secondary cross-check > existing direct Waller/Tomoshi/core > Waller/OpenJLPT exact evidence > calibrated model only for residual estimated rows",
    })
    CORE.write_text(
        "// AUTO-GENERATED JLPT-recalibrated core overlay. Do not edit by hand.\n"
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
        "version": "prebuilt-20260826-v7-world-jlpt",
        "generated": datetime.now(timezone.utc).isoformat(),
        "countsByLevel": {x: counts.get(x, 0) for x in ["N1","N2","N3","N4","N5"]},
        "levelSources": dict(sources),
        "jlptRecalibration": recal,
        "levelPolicy": "direct world/community evidence first; residual labels estimated by model calibrated on direct-labelled runtime words; missing frequency never implies N1",
    })
    ADV.write_text(
        "// AUTO-GENERATED world-evidence JLPT recalibration. Do not edit by hand.\n"
        "(()=>{\"use strict\";\n" + f"const M={json.dumps(meta,ensure_ascii=False,separators=(',',':'))},T={json.dumps(tuples,ensure_ascii=False,separators=(',',':'))};\n" +
        "window.ADVANCED_WORDS=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];const base=window.ADVANCED_WORDS.length;"
        "for(let i=0;i<T.length;i++){const x=T[i];window.ADVANCED_WORDS.push({id:`bundle-${i}`,level:x[0],reading:x[1],kanji:x[2]||\"\",displayWord:x[2]||x[1],meaning:x[3],pos:x[4]||\"other\",estimated:String(x[5]||\"\").includes(\"estimate\"),levelSource:x[5]||\"\",entryId:x[6]||null,qualityTier:x[7]||\"\",jlptConfidence:x[8]??null,frequencyRank:x[9]??null,source:\"進階補充詞（世界 JLPT 證據交叉校準）\"});}"
        "window.ADVANCED_WORDS_BUNDLE_META={...M,loadedCount:window.ADVANCED_WORDS.length-base};window.VOCAB_JLPT_RECALIBRATION_META=M.jlptRecalibration;})();\n",
        encoding="utf-8")


def main():
    if not DB.exists():
        raise RuntimeError(f"Tomoshi DB missing: {DB}")
    adv_meta, adv_raw = load_bundle()
    core_meta, core_raw = load_core()
    conn = sqlite3.connect(str(DB))
    common, ranks = load_db_evidence(conn)
    waller_id, waller_key = load_waller()
    open_key, open_counts = load_openjlpt()
    manual = load_manual_secondary()

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

    conflicts1, added1 = apply_world_evidence(core, waller_id, waller_key, open_key, manual)
    conflicts2, added2 = apply_world_evidence(advanced, waller_id, waller_key, open_key, manual)
    training_pool = core + advanced
    model, train_counts, medians, n1_floor = train_model(training_pool)
    predicted = Counter()
    n1_without_rank = 0
    for r in training_pool:
        if r.get("direct"):
            r["confidence"] = None
            continue
        lvl, conf, _scores = predict(r, model, n1_floor)
        r["level"] = lvl
        r["level_source"] = "world-calibrated-estimate"
        r["confidence"] = conf
        predicted[lvl] += 1
        if lvl == "N1" and not r.get("rank"):
            n1_without_rank += 1

    combined_counts = Counter(r["level"] for r in training_pool)
    direct_counts = Counter(r["level"] for r in training_pool if r.get("direct"))
    estimated_counts = Counter(r["level"] for r in training_pool if not r.get("direct"))
    if n1_without_rank:
        raise RuntimeError(f"N1 positive-evidence gate failed: {n1_without_rank} estimated N1 rows have no observed frequency rank")
    if combined_counts["N1"] >= 15000:
        raise RuntimeError(f"N1 distribution still implausibly inflated: {combined_counts}")
    suika = next((r for r in core + advanced if r["key"] == "すいか|西瓜"), None)
    if not suika or suika["level"] != "N5":
        raise RuntimeError(f"西瓜 sentinel failed after world recalibration: {suika}")

    recal = {
        "status":"complete",
        "version":"20260826-world-v1",
        "sources":["existing core/Waller/Tomoshi direct labels","Japanese Language Data Waller/Tanos CC-BY-SA","OpenJLPT CC-BY-SA","Mazii/MOJi/時雨 exact manual secondary cross-check layer","Tomoshi/JMdict frequency/commonness for residual model features"],
        "policy":"Direct exact/community evidence is preserved or added first. Only residual unlabelled rows are model-estimated. Missing frequency is never N1 evidence; estimated N1 requires an observed rank and model margin.",
        "trainingDirectRows":sum(train_counts.values()),
        "trainingCountsByLevel":dict(train_counts),
        "directCountsByLevel":dict(direct_counts),
        "estimatedCountsByLevel":dict(estimated_counts),
        "combinedCountsByLevel":dict(combined_counts),
        "newDirectEvidence":dict(added1 + added2),
        "openJlptPublishedCounts":open_counts,
        "modelRankLogMedians":medians,
        "modelN1RankLogFloor":n1_floor,
        "estimatedN1WithoutObservedRank":n1_without_rank,
        "worldEvidenceConflictCount":len(conflicts1)+len(conflicts2),
        "worldEvidenceConflictSamples":(conflicts1+conflicts2)[:100],
        "manualSecondaryExactConfigured":len(manual),
    }
    write_core(core_meta, core)
    write_advanced(adv_meta, advanced, recal)
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    audit["jlptRecalibration"] = recal
    audit.setdefault("counts", {})["jlptCountsCoreAdvanced"] = {x: combined_counts.get(x,0) for x in ["N1","N2","N3","N4","N5"]}
    audit.setdefault("policy", {})["jlptLevel"] = recal["policy"]
    AUDIT.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(recal, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
