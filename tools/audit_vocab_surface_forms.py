#!/usr/bin/env python3
"""Strict surface-form JLPT vocabulary audit.

Coverage rule: a reference item is covered ONLY when the runtime database has
that same written form and reading after Unicode/kana normalization.

Different written forms are separate learning items even when they share a
reading or JMdict entry (e.g. 川/河, 温まる/暖まる, 気づく/気付く).
JMdict relations are annotations only and never suppress a missing item.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import audit_vocab_coverage as A
import refine_vocab_audit_jmdict as J

ROOT = Path(__file__).resolve().parents[1]


def load_manual_coverage(path: Path) -> list[A.Entry]:
    """Load the reviewed deferred completion layer used by the browser runtime."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for i, row in enumerate(data.get("entries") or []):
        if not isinstance(row, list) or len(row) < 4:
            continue
        level, reading, word, meaning = row[:4]
        word = str(word or reading or "").strip()
        reading = str(reading or "").strip()
        meaning = str(meaning or "").strip()
        if word and reading and level in A.LEVELS and meaning:
            out.append(A.Entry("coverage-manual", str(level), word, reading, meaning, f"manual-{i}"))
    return A.dedupe_entries(out)


def load_runtime() -> list[A.Entry]:
    core_text, _ = A.first_text(A.CORE_URLS)
    _, runtime_core, _ = A.parse_core(core_text)
    curated = A.load_curated(ROOT / "advanced_words_curated.js")
    advanced = A.load_advanced_bundle(ROOT / "data" / "advanced_vocab.js")
    manual = load_manual_coverage(ROOT / "data" / "coverage_manual_meanings.json")
    return A.dedupe_entries([*runtime_core, *curated, *advanced, *manual])


def csv_write(path: Path, rows: list[dict], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def relation_for(ref: A.Entry, runtime: list[A.Entry], runtime_by_reading, runtime_by_word,
                 word_ids, reading_ids, forms_by_id, current_clusters, current_by_cluster) -> dict:
    rd = A.normalize_reading(ref.reading)
    word = A.normalize_word(ref.word)
    same_reading = [e for e in runtime_by_reading.get(rd, []) if A.normalize_word(e.word) != word]
    same_word = [e for e in runtime_by_word.get(word, []) if A.normalize_reading(e.reading) != rd]

    ids = J.resolve(ref, word_ids, reading_ids)
    overlap = sorted(ids & current_clusters)
    jmdict_matches = []
    jmdict_forms = []
    for cid in overlap:
        jmdict_matches.extend(current_by_cluster[cid])
        forms = forms_by_id.get(cid, {})
        jmdict_forms.extend(forms.get("kanji") or [])
        jmdict_forms.extend(forms.get("kana") or [])

    relation_types = []
    if same_reading:
        relation_types.append("same-reading-different-writing")
    if same_word:
        relation_types.append("same-writing-different-reading")
    if overlap:
        relation_types.append("same-jmdict-entry")
    if not relation_types:
        relation_types.append("fully-absent")

    return {
        "relation_type": "|".join(relation_types),
        "same_reading_current_forms": "|".join(sorted({e.word for e in same_reading}))[:1500],
        "same_word_current_readings": "|".join(sorted({e.reading for e in same_word}))[:1000],
        "jmdict_current_forms": "|".join(sorted({e.word for e in jmdict_matches}))[:1500],
        "jmdict_current_readings": "|".join(sorted({e.reading for e in jmdict_matches}))[:1000],
        "jmdict_current_levels": "|".join(sorted({e.level for e in jmdict_matches if e.level})),
        "jmdict_all_forms": "|".join(sorted(set(jmdict_forms)))[:2000],
        "jmdict_resolved": "yes" if ids else "no",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="audit/vocab/results")
    args = p.parse_args()
    out = Path(args.results)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    runtime = load_runtime()
    refs, inventory, errors = A.load_references()
    ref_groups = A.reference_groups(refs)

    runtime_exact = {e.exact_key for e in runtime}
    runtime_by_reading = defaultdict(list)
    runtime_by_word = defaultdict(list)
    for e in runtime:
        runtime_by_reading[A.normalize_reading(e.reading)].append(e)
        runtime_by_word[A.normalize_word(e.word)].append(e)

    word_ids, reading_ids, forms_by_id, jmdict_url = J.load_jmdict_clusters()
    current_clusters = set()
    current_by_cluster = defaultdict(list)
    for e in runtime:
        for cid in J.resolve(e, word_ids, reading_ids):
            current_clusters.add(cid)
            current_by_cluster[cid].append(e)

    missing_high = []
    missing_single = []
    covered = []
    relations = []

    for _, group in sorted(ref_groups.items(), key=lambda kv: kv[0]):
        example = group[0]
        sources = sorted({e.source for e in group})
        families = sorted({A.SOURCE_FAMILY.get(e.source, e.source) for e in group})
        consensus_level, level_votes, family_level_votes = A.mode_level(group)
        base = {
            "word": example.word,
            "reading": example.reading,
            "consensus_level": consensus_level,
            "level_votes": json.dumps(level_votes, ensure_ascii=False, sort_keys=True),
            "family_level_votes": json.dumps(family_level_votes, ensure_ascii=False, sort_keys=True),
            "reference_sources": "|".join(sources),
            "reference_families": "|".join(families),
            "support_count": len(families),
            "candidate_type": A.candidate_type(example.word, example.reading),
            "example_meaning": next((e.meaning for e in group if e.meaning), ""),
        }
        if example.exact_key in runtime_exact:
            covered.append(base)
            continue

        rel = relation_for(example, runtime, runtime_by_reading, runtime_by_word,
                           word_ids, reading_ids, forms_by_id, current_clusters, current_by_cluster)
        row = {**base, **rel}
        relations.append(row)
        if len(families) >= 2:
            missing_high.append(row)
        else:
            missing_single.append(row)

    def level_counts(rows):
        c = Counter(r.get("consensus_level") or "Unknown" for r in rows)
        return {lv: c.get(lv, 0) for lv in A.LEVELS}

    relation_counts = Counter()
    for row in relations:
        for t in (row.get("relation_type") or "").split("|"):
            if t:
                relation_counts[t] += 1

    consensus_denoms = Counter()
    consensus_missing = Counter()
    for _, group in ref_groups.items():
        families = {A.SOURCE_FAMILY.get(e.source, e.source) for e in group}
        if len(families) < 2:
            continue
        level, _, _ = A.mode_level(group)
        if level in A.LEVELS:
            consensus_denoms[level] += 1
            if group[0].exact_key not in runtime_exact:
                consensus_missing[level] += 1

    consensus_summary = {}
    for lv in A.LEVELS:
        d = consensus_denoms[lv]
        m = consensus_missing[lv]
        consensus_summary[lv] = {
            "consensus_reference_unique": d,
            "exact_surface_missing": m,
            "exact_surface_covered": d - m,
            "exact_surface_coverage_pct": round((d - m) * 100 / d, 2) if d else None,
        }

    summary = {
        "coverage_rule": "ONLY exact normalized written-form + reading counts as covered; different kanji/kana spellings remain separate items",
        "jmdict_role": "annotation only; same JMdict entry never suppresses a missing surface form",
        "jmdict_source": jmdict_url,
        "runtime_unique": len(runtime_exact),
        "reference_exact_groups": len(ref_groups),
        "exact_surface_missing_high_confidence": len(missing_high),
        "exact_surface_missing_single_source": len(missing_single),
        "exact_surface_missing_all": len(relations),
        "high_confidence_by_level": level_counts(missing_high),
        "single_source_by_level": level_counts(missing_single),
        "relation_counts": dict(sorted(relation_counts.items())),
        "consensus_level_summary": consensus_summary,
        "source_inventory": inventory,
        "source_errors": errors,
        "runtime_sources": {
            "core": "upstream core CSV accepted by runtime parser",
            "curated": "advanced_words_curated.js",
            "advanced": "data/advanced_vocab.js",
            "manual_reviewed_completion": "data/coverage_manual_meanings.json",
        },
    }
    (out / "surface_form_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    cols = [
        "word","reading","consensus_level","level_votes","family_level_votes","reference_sources",
        "reference_families","support_count","candidate_type","example_meaning","relation_type",
        "same_reading_current_forms","same_word_current_readings","jmdict_current_forms",
        "jmdict_current_readings","jmdict_current_levels","jmdict_all_forms","jmdict_resolved",
    ]
    csv_write(out / "missing_surface_high_confidence.csv", missing_high, cols)
    csv_write(out / "missing_surface_single_source.csv", missing_single, cols)
    csv_write(out / "surface_form_relations.csv", relations, cols)

    md = [
        "# Strict Surface-Form Vocabulary Coverage Audit",
        "",
        "**Rule:** only the same written form + reading counts as covered. Same reading or same JMdict entry is not coverage.",
        "",
        f"- Runtime unique exact items: **{len(runtime_exact):,}**",
        f"- High-confidence exact-form missing: **{len(missing_high):,}**",
        f"- Single-source exact-form missing: **{len(missing_single):,}**",
        f"- All exact-form missing candidates: **{len(relations):,}**",
        "",
        "## Consensus exact-surface coverage",
        "",
        "| Level | Consensus items | Exact covered | Exact missing | Coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for lv in A.LEVELS:
        x = consensus_summary[lv]
        md.append(f"| {lv} | {x['consensus_reference_unique']:,} | {x['exact_surface_covered']:,} | {x['exact_surface_missing']:,} | {x['exact_surface_coverage_pct']}% |")
    md += ["", "## Relation counts among missing forms", ""]
    for k, v in sorted(relation_counts.items()):
        md.append(f"- {k}: **{v:,}**")
    md += [
        "",
        "`surface_form_relations.csv` lists every missing surface form and any current same-reading / same-JMdict related form. Those relations are annotations only.",
        "",
    ]
    (out / "SURFACE_FORM_AUDIT.md").write_text("\n".join(md), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
