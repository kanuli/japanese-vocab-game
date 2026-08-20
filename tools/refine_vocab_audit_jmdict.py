#!/usr/bin/env python3
"""Refine high-confidence JLPT coverage gaps with JMdict lexical identity.

A surface-form comparison can still report false gaps when the site contains a
JMdict-equivalent spelling or reading. This script separates those cases from
true lexical gaps. It does not modify vocabulary data.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import audit_vocab_coverage as A

ROOT = Path(__file__).resolve().parents[1]
JMDICT_URLS = [
    "https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/core/words.json",
    "https://cdn.jsdelivr.net/gh/jkindrix/japanese-language-data@main/data/core/words.json",
]


def load_jmdict_clusters():
    text, source_url = A.first_text(JMDICT_URLS)
    data = json.loads(text)
    rows = data.get("words") if isinstance(data, dict) else data
    word_ids: dict[str, set[int]] = defaultdict(set)
    reading_ids: dict[str, set[int]] = defaultdict(set)
    forms_by_id: dict[int, dict] = {}

    for idx, raw in enumerate(rows or []):
        kanji = [str(x.get("text") or "").strip() for x in (raw.get("kanji") or []) if str(x.get("text") or "").strip()]
        kana_items = [x for x in (raw.get("kana") or []) if str(x.get("text") or "").strip()]
        kana = [str(x.get("text") or "").strip() for x in kana_items]
        if not kanji and not kana:
            continue
        cluster_id = idx
        for form in kanji:
            word_ids[A.normalize_word(form)].add(cluster_id)
        for rd in kana:
            norm = A.normalize_reading(rd)
            reading_ids[norm].add(cluster_id)
            # Kana-only / kana spelling lookup.
            word_ids[A.normalize_word(rd)].add(cluster_id)
        forms_by_id[cluster_id] = {"kanji": kanji, "kana": kana}

    return word_ids, reading_ids, forms_by_id, source_url


def resolve(entry: A.Entry, word_ids, reading_ids) -> set[int]:
    w = A.normalize_word(entry.word)
    r = A.normalize_reading(entry.reading)
    wi = set(word_ids.get(w, set()))
    ri = set(reading_ids.get(r, set()))
    if wi and ri:
        inter = wi & ri
        if inter:
            return inter
    # When the written form is kana, reading identity is the safer fallback.
    if A.is_kana(entry.word) and ri:
        return ri
    return set()


def load_current_runtime() -> list[A.Entry]:
    core_text, _ = A.first_text(A.CORE_URLS)
    _, runtime_core, _ = A.parse_core(core_text)
    curated = A.load_curated(ROOT / "advanced_words_curated.js")
    advanced = A.load_advanced_bundle(ROOT / "data" / "advanced_vocab.js")
    return A.dedupe_entries([*runtime_core, *curated, *advanced])


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="audit/vocab/results")
    args = parser.parse_args()
    results = Path(args.results)
    if not results.is_absolute():
        results = ROOT / results

    source = results / "missing_high_confidence.csv"
    if not source.exists():
        print(f"missing prerequisite: {source}", file=sys.stderr)
        return 2

    current = load_current_runtime()
    word_ids, reading_ids, forms_by_id, jmdict_url = load_jmdict_clusters()

    current_clusters: set[int] = set()
    current_by_cluster: dict[int, list[A.Entry]] = defaultdict(list)
    for entry in current:
        ids = resolve(entry, word_ids, reading_ids)
        for cid in ids:
            current_clusters.add(cid)
            current_by_cluster[cid].append(entry)

    raw_missing = read_csv(source)
    refined: list[dict] = []
    related: list[dict] = []
    unresolved_jmdict: list[dict] = []

    for row in raw_missing:
        entry = A.Entry(
            "audit-candidate",
            row.get("consensus_level") or "",
            row.get("word") or "",
            row.get("reading") or "",
            row.get("example_meaning") or "",
        )
        ids = resolve(entry, word_ids, reading_ids)
        overlap = sorted(ids & current_clusters)
        if overlap:
            matches = []
            jmdict_forms = []
            for cid in overlap:
                matches.extend(current_by_cluster[cid])
                forms = forms_by_id.get(cid, {})
                jmdict_forms.extend(forms.get("kanji") or [])
                jmdict_forms.extend(forms.get("kana") or [])
            related.append({
                **row,
                "relation": "same-jmdict-entry",
                "current_forms": "|".join(sorted({x.word for x in matches})),
                "current_readings": "|".join(sorted({x.reading for x in matches})),
                "current_levels": "|".join(sorted({x.level for x in matches if x.level})),
                "jmdict_forms": "|".join(sorted(set(jmdict_forms)))[:1200],
            })
        else:
            refined.append(row)
            if not ids:
                unresolved_jmdict.append(row)

    by_level = Counter(x.get("consensus_level") or "Unknown" for x in refined)
    related_by_level = Counter(x.get("consensus_level") or "Unknown" for x in related)
    by_type = Counter(x.get("candidate_type") or "Unknown" for x in refined)

    summary_path = results / "coverage_summary.json"
    base_summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
    consensus = base_summary.get("consensus_level_summary") or {}
    refined_level_summary = {}
    for level in A.LEVELS:
        denominator = int((consensus.get(level) or {}).get("consensus_reference_unique") or 0)
        missing = int(by_level.get(level, 0))
        refined_level_summary[level] = {
            "consensus_reference_unique": denominator,
            "refined_missing": missing,
            "refined_lexical_coverage_pct": round((denominator - missing) * 100 / denominator, 2) if denominator else None,
        }

    summary = {
        "jmdict_source": jmdict_url,
        "input_high_confidence_missing": len(raw_missing),
        "same_jmdict_entry_relations": len(related),
        "refined_missing": len(refined),
        "jmdict_unresolved_candidates": len(unresolved_jmdict),
        "refined_missing_by_level": {k: by_level.get(k, 0) for k in A.LEVELS},
        "jmdict_related_by_level": {k: related_by_level.get(k, 0) for k in A.LEVELS},
        "refined_missing_by_type": dict(sorted(by_type.items())),
        "refined_level_summary": refined_level_summary,
        "interpretation": (
            "refined_missing excludes candidates whose exact surface form is absent but whose word/reading resolves "
            "to a JMdict lexical entry already represented by the current runtime vocabulary."
        ),
    }

    base_cols = [
        "word","reading","consensus_level","level_votes","family_level_votes","reference_sources",
        "reference_families","support_count","candidate_type","example_meaning",
    ]
    write_csv(results / "missing_refined.csv", refined, base_cols)
    write_csv(results / "jmdict_related.csv", related,
              base_cols + ["relation","current_forms","current_readings","current_levels","jmdict_forms"])
    write_csv(results / "jmdict_unresolved.csv", unresolved_jmdict, base_cols)
    (results / "refined_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Refined JLPT Missing-Vocabulary Audit (JMdict-aware)",
        "",
        f"Input high-confidence surface-form gaps: **{len(raw_missing):,}**",
        f"Reclassified as same JMdict lexical entry already represented: **{len(related):,}**",
        f"Remaining refined missing candidates: **{len(refined):,}**",
        "",
        "## Refined missing by level",
        "",
        "| Level | Consensus reference | Refined missing | Lexical coverage |",
        "|---|---:|---:|---:|",
    ]
    for level in A.LEVELS:
        x = refined_level_summary[level]
        md.append(f"| {level} | {x['consensus_reference_unique']:,} | {x['refined_missing']:,} | {x['refined_lexical_coverage_pct']}% |")
    md += [
        "",
        "## Remaining candidate types",
        "",
    ]
    for key, value in sorted(by_type.items()):
        md.append(f"- {key}: **{value:,}**")
    md += [
        "",
        "`missing_refined.csv` is the recommended manual-review queue. `jmdict_related.csv` contains spelling/reading variants that should not be treated as a missing lexical item automatically.",
        "",
    ]
    (results / "README_REFINED.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
