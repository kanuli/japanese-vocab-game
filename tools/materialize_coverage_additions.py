#!/usr/bin/env python3
"""Materialize reviewed strict-surface vocabulary additions.

Modes:
- direct: ADD_HIGH_CONFIDENCE + ADD_DISTINCT_VARIANT
- source-check: only rows approved by source-check adjudication

Every exact written form + reading pair is independent. Traditional-Chinese
meanings are mandatory. Meaning lookup uses the same JA->ZH source pipeline as
the main vocabulary builder; unresolved items are deferred, never guessed.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from opencc import OpenCC

import audit_vocab_coverage as A
import build_vocab_bundle as B

ROOT = Path(__file__).resolve().parents[1]
LEVELS = set(A.LEVELS)
CJK_RE = re.compile(r"[\u3400-\u9fff]")
DIRECT_DECISIONS = {"ADD_HIGH_CONFIDENCE", "ADD_DISTINCT_VARIANT"}
SOURCE_CHECK_DECISIONS = {"ADD_AFTER_SOURCE_CHECK", "ADD_VARIANT_AFTER_SOURCE_CHECK"}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def split_pipe(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split("|") if x.strip()]


def load_manual_runtime(path: Path) -> list[A.Entry]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for i, row in enumerate(data.get("entries") or []):
        if not isinstance(row, list) or len(row) < 4:
            continue
        level, reading, word, meaning = row[:4]
        if str(level) in LEVELS and str(reading).strip() and str(word).strip() and str(meaning).strip():
            out.append(A.Entry("coverage-manual", str(level), str(word).strip(), str(reading).strip(), str(meaning).strip(), f"manual-{i}"))
    return A.dedupe_entries(out)


def load_runtime_entries() -> list[A.Entry]:
    core_text, _ = A.first_text(A.CORE_URLS)
    _, runtime_core, _ = A.parse_core(core_text)
    curated = A.load_curated(ROOT / "advanced_words_curated.js")
    advanced = A.load_advanced_bundle(ROOT / "data" / "advanced_vocab.js")
    manual = load_manual_runtime(ROOT / "data" / "coverage_manual_meanings.json")
    return A.dedupe_entries([*runtime_core, *curated, *advanced, *manual])


def pos_from_review(value: str) -> str:
    text = str(value or "")
    if re.search(r"(?:^|\|)v(?:\d|s|i|t|1|5)|verb", text, re.I): return "verb"
    if "adj" in text.lower(): return "adj"
    if "adv" in text.lower(): return "adv"
    if re.search(r"(?:^|\|)n(?::|\||$)|noun", text, re.I): return "noun"
    if "conj" in text.lower(): return "conj"
    if "prt" in text.lower() or "particle" in text.lower(): return "particle"
    return "other"


def choose_level(row: dict) -> tuple[str, str]:
    consensus = (row.get("publish_level") or row.get("consensus_level") or "").upper()
    waller = [x for x in split_pipe(row.get("jmdict_waller_levels") or "") if x in LEVELS]
    conflict = (row.get("level_conflict_with_jmdict_waller") or "").lower() == "yes"
    confidence = row.get("evidence_confidence") or ""
    if confidence == "HIGH" and consensus in LEVELS:
        return consensus, "independent-reference-consensus" + (";waller-conflict" if conflict else "")
    if consensus in LEVELS:
        return consensus, "single-reference-estimated" + (";waller-conflict" if conflict else "")
    if len(set(waller)) == 1:
        return waller[0], "jmdict-waller"
    return "N1", "fallback-N1"


def select_rows(mode: str, results: Path) -> list[dict]:
    if mode == "source-check":
        p = results / "source_check_approved.csv"
        if not p.exists():
            raise SystemExit("source_check_approved.csv missing; run adjudicate_source_check.py first")
        rows = read_csv(p)
        return [r for r in rows if str(r.get("source_check_decision") or "").startswith("APPROVE")]
    p = results / "final_quality_review_all_missing.csv"
    rows = read_csv(p)
    return [r for r in rows if str(r.get("quality_decision") or "") in DIRECT_DECISIONS]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="audit/vocab/results")
    p.add_argument("--output", default="data/coverage_additions.json")
    p.add_argument("--mode", choices=("direct", "source-check"), default="direct")
    args = p.parse_args()
    results = Path(args.results); output = Path(args.output)
    if not results.is_absolute(): results = ROOT / results
    if not output.is_absolute(): output = ROOT / output

    rows = select_rows(args.mode, results)
    converter = OpenCC("s2hk")
    runtime = load_runtime_entries()
    runtime_exact = {e.exact_key for e in runtime}
    runtime_by_word: dict[str, list[A.Entry]] = defaultdict(list)
    for e in runtime: runtime_by_word[A.normalize_word(e.word)].append(e)

    wanted = {str(r.get("word") or "").strip() for r in rows if str(r.get("word") or "").strip()}
    meanings, meaning_stats = B.load_meanings(wanted, converter)

    additions=[]; deferred=[]; seen=set(); source_counts=Counter(); decision_counts=Counter(); level_counts=Counter()
    for row in rows:
        word=str(row.get("word") or "").strip(); reading=str(row.get("reading") or "").strip()
        if not word or not reading:
            deferred.append({**row,"defer_reason":"missing-word-or-reading"}); continue
        key=A.exact_key(word,reading)
        if key in runtime_exact or key in seen: continue
        meaning=""; meaning_source=""

        pinned=str(row.get("pinned_tc_meaning") or "").strip()
        if pinned and CJK_RE.search(pinned):
            meaning=pinned; meaning_source="source-check-pinned-sense"
        if not meaning:
            value=meanings.get(word,"")
            if value: meaning=value; meaning_source="open-ja-zh-exact-form"
        if not meaning:
            raw=str(row.get("example_meaning") or "").strip()
            if raw and CJK_RE.search(raw):
                value=B.clean_meaning(raw,converter)
                if value: meaning=value; meaning_source="review-source-cjk"
        if not meaning and "same-jmdict-entry" in str(row.get("relation_type") or ""):
            for form in split_pipe(row.get("jmdict_current_forms") or ""):
                for entry in runtime_by_word.get(A.normalize_word(form),[]):
                    if entry.meaning and CJK_RE.search(entry.meaning):
                        value=B.clean_meaning(entry.meaning,converter)
                        if value:
                            meaning=value; meaning_source="existing-related-runtime-tc"; break
                if meaning: break
        if not meaning:
            deferred.append({**row,"defer_reason":"no-reliable-traditional-chinese-meaning-after-full-source-scan"}); continue

        level,level_source=choose_level(row)
        item={"level":level,"reading":reading,"word":word,"meaning":meaning,"pos":pos_from_review(row.get("jmdict_pos") or ""),
              "decision":row.get("quality_decision") or "","source_check_decision":row.get("source_check_decision") or "",
              "priority":row.get("priority") or "","evidence_confidence":row.get("evidence_confidence") or "",
              "reference_sources":row.get("reference_sources") or "","reference_families":row.get("reference_families") or "",
              "relation_type":row.get("relation_type") or "","meaning_source":meaning_source,"level_source":level_source}
        additions.append(item); seen.add(key); source_counts[meaning_source]+=1; decision_counts[item["source_check_decision"] or item["decision"]]+=1; level_counts[level]+=1

    additions.sort(key=lambda x:(A.LEVELS.index(x["level"]) if x["level"] in A.LEVELS else 99,A.normalize_reading(x["reading"]),A.normalize_word(x["word"])))
    prefix="source_check" if args.mode=="source-check" else "coverage_additions"
    summary={"version":"coverage-materializer-v4","generated_at_utc":datetime.now(timezone.utc).isoformat(),"mode":args.mode,
             "rule":"Every written form + reading is independent; related forms never suppress an addition.","eligible_rows":len(rows),
             "already_present":len(rows)-len(additions)-len(deferred),"materialized_count":len(additions),"deferred_count":len(deferred),
             "meaning_source_counts":dict(sorted(source_counts.items())),"decision_counts":dict(sorted(decision_counts.items())),
             "level_counts":{lv:level_counts.get(lv,0) for lv in A.LEVELS},"meaning_lookup_stats":meaning_stats}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({**summary,"additions":additions},ensure_ascii=False,indent=2),encoding="utf-8")
    defer_cols=list(rows[0].keys())+["defer_reason"] if rows else ["defer_reason"]
    write_csv(results/f"{prefix}_deferred.csv",deferred,defer_cols)
    (results/f"{prefix}_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
