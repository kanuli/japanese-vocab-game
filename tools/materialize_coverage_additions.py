#!/usr/bin/env python3
"""Materialize reviewed strict-coverage additions for the vocabulary bundle.

Only quality-review rows whose decision starts with ADD are eligible. Each
written-form + reading pair remains independent. Traditional-Chinese meanings
are required before an item is emitted.

Meaning priority:
1. exact Japanese form from the existing open JA->ZH sources used by the main builder,
2. Traditional-Chinese meaning already present on a JMdict-related runtime form,
3. CJK meaning already present in the reviewed source row.

Rows without a reliable Traditional-Chinese meaning are deferred rather than
falling back to English.
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


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def split_pipe(value: str) -> list[str]:
    return [x.strip() for x in str(value or "").split("|") if x.strip()]


def load_runtime_entries() -> list[A.Entry]:
    core_text, _ = A.first_text(A.CORE_URLS)
    _, runtime_core, _ = A.parse_core(core_text)
    curated = A.load_curated(ROOT / "advanced_words_curated.js")
    advanced = A.load_advanced_bundle(ROOT / "data" / "advanced_vocab.js")
    return A.dedupe_entries([*runtime_core, *curated, *advanced])


def pos_from_review(value: str) -> str:
    text = str(value or "")
    if re.search(r"(?:^|\|)v(?:\d|s|i|t|1|5)|verb", text, re.I):
        return "verb"
    if "adj" in text.lower():
        return "adj"
    if "adv" in text.lower():
        return "adv"
    if re.search(r"(?:^|\|)n(?::|\||$)|noun", text, re.I):
        return "noun"
    if "conj" in text.lower():
        return "conj"
    if "prt" in text.lower() or "particle" in text.lower():
        return "particle"
    return "other"


def choose_level(row: dict) -> tuple[str, str]:
    confidence = row.get("evidence_confidence") or ""
    consensus = (row.get("consensus_level") or "").upper()
    waller = [x for x in split_pipe(row.get("jmdict_waller_levels") or "") if x in LEVELS]
    conflict = (row.get("level_conflict_with_jmdict_waller") or "").lower() == "yes"

    # Two independent reference families take precedence for the audit target.
    if confidence == "HIGH" and consensus in LEVELS:
        return consensus, "independent-reference-consensus" + (";waller-conflict" if conflict else "")
    # Single-source additions are safer when anchored to JMdict/Waller enrichment.
    if len(set(waller)) == 1:
        return waller[0], "jmdict-waller"
    if consensus in LEVELS:
        return consensus, "single-reference-level-estimate"
    return "N1", "fallback-N1"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="audit/vocab/results")
    p.add_argument("--output", default="data/coverage_additions.json")
    args = p.parse_args()

    results = Path(args.results)
    if not results.is_absolute():
        results = ROOT / results
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output

    review_path = results / "final_quality_review_all_missing.csv"
    if not review_path.exists():
        raise SystemExit(f"missing review input: {review_path}")

    rows = [r for r in read_csv(review_path) if str(r.get("quality_decision") or "").startswith("ADD")]
    converter = OpenCC("s2hk")
    runtime = load_runtime_entries()

    runtime_by_word: dict[str, list[A.Entry]] = defaultdict(list)
    runtime_exact = {e.exact_key for e in runtime}
    for e in runtime:
        runtime_by_word[A.normalize_word(e.word)].append(e)

    wanted = {str(r.get("word") or "").strip() for r in rows if str(r.get("word") or "").strip()}
    # Related JMdict forms can supply an already-curated TC meaning, but only after
    # exact-form dictionary lookup has been attempted.
    for r in rows:
        wanted.update(split_pipe(r.get("jmdict_current_forms") or ""))

    meanings, meaning_stats = B.load_meanings(wanted, converter)

    additions = []
    deferred = []
    seen = set()
    source_counts = Counter()
    decision_counts = Counter()
    level_counts = Counter()

    for row in rows:
        word = str(row.get("word") or "").strip()
        reading = str(row.get("reading") or "").strip()
        if not word or not reading:
            deferred.append({**row, "defer_reason": "missing-word-or-reading"})
            continue
        key = A.exact_key(word, reading)
        if key in runtime_exact:
            # Defensive: post-review changes may already have filled the item.
            continue
        if key in seen:
            continue

        meaning = ""
        meaning_source = ""

        exact_meaning = meanings.get(word, "")
        if exact_meaning:
            meaning = exact_meaning
            meaning_source = "open-ja-zh-exact-form"

        if not meaning:
            for form in split_pipe(row.get("jmdict_current_forms") or ""):
                for entry in runtime_by_word.get(A.normalize_word(form), []):
                    if entry.meaning and CJK_RE.search(entry.meaning):
                        meaning = converter.convert(entry.meaning).strip()
                        meaning_source = "existing-jmdict-related-runtime"
                        break
                if meaning:
                    break

        if not meaning:
            raw = str(row.get("example_meaning") or "").strip()
            if raw and CJK_RE.search(raw):
                meaning = B.clean_meaning(raw, converter)
                if meaning:
                    meaning_source = "review-source-cjk"

        if not meaning:
            deferred.append({**row, "defer_reason": "no-reliable-traditional-chinese-meaning"})
            continue

        level, level_source = choose_level(row)
        pos = pos_from_review(row.get("jmdict_pos") or "")
        item = {
            "level": level,
            "reading": reading,
            "word": word,
            "meaning": meaning,
            "pos": pos,
            "decision": row.get("quality_decision") or "",
            "priority": row.get("priority") or "",
            "evidence_confidence": row.get("evidence_confidence") or "",
            "reference_sources": row.get("reference_sources") or "",
            "reference_families": row.get("reference_families") or "",
            "relation_type": row.get("relation_type") or "",
            "meaning_source": meaning_source,
            "level_source": level_source,
        }
        additions.append(item)
        seen.add(key)
        source_counts[meaning_source] += 1
        decision_counts[item["decision"]] += 1
        level_counts[level] += 1

    additions.sort(key=lambda x: (A.LEVELS.index(x["level"]) if x["level"] in A.LEVELS else 99, A.normalize_reading(x["reading"]), A.normalize_word(x["word"])))

    payload = {
        "version": "coverage-additions-v1-strict-surface-form",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "rule": "Every written form + reading is independent; same-reading/JMdict-related forms never suppress an addition.",
        "source_review": str(review_path.relative_to(ROOT)),
        "eligible_add_rows": len(rows),
        "materialized_count": len(additions),
        "deferred_count": len(deferred),
        "meaning_source_counts": dict(sorted(source_counts.items())),
        "decision_counts": dict(sorted(decision_counts.items())),
        "level_counts": {lv: level_counts.get(lv, 0) for lv in A.LEVELS},
        "builder_meaning_source_stats": meaning_stats,
        "additions": additions,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    defer_cols = list(rows[0].keys()) + ["defer_reason"] if rows else ["defer_reason"]
    write_csv(results / "coverage_additions_deferred.csv", deferred, defer_cols)
    (results / "coverage_additions_summary.json").write_text(json.dumps({k: v for k, v in payload.items() if k != "additions"}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({k: v for k, v in payload.items() if k != "additions"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
