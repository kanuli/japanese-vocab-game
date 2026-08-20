#!/usr/bin/env python3
"""Final quality review for strict missing vocabulary surface forms.

Consumes both high-confidence and single-source strict missing lists. Every
written form + reading pair is reviewed independently. Same-reading or
same-JMdict alternatives never cause exclusion by themselves.
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


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], cols: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_jmdict_details():
    text, source_url = A.first_text(J.JMDICT_URLS)
    data = json.loads(text)
    rows = data.get("words") if isinstance(data, dict) else data
    tags_map = (data.get("metadata") or {}).get("tags") or {} if isinstance(data, dict) else {}
    exact = defaultdict(list)
    by_word = defaultdict(list)

    for raw in rows or []:
        kanji_items = [x for x in (raw.get("kanji") or []) if str(x.get("text") or "").strip()]
        kana_items = [x for x in (raw.get("kana") or []) if str(x.get("text") or "").strip()]
        senses = raw.get("sense") or []
        glosses = []
        misc = []
        info = []
        pos = []
        dialect = []
        for s in senses:
            for g in s.get("gloss") or []:
                if (g.get("lang") or "eng") == "eng" and g.get("text"):
                    glosses.append(str(g.get("text")))
            misc.extend(str(x) for x in (s.get("misc") or []))
            info.extend(str(x) for x in (s.get("info") or []))
            pos.extend(str(x) for x in (s.get("partOfSpeech") or []))
            dialect.extend(str(x) for x in (s.get("dialect") or []))

        for k in kanji_items:
            word = str(k.get("text") or "").strip()
            for kana in kana_items:
                rd = str(kana.get("text") or "").strip()
                applies = kana.get("appliesToKanji") or []
                if applies and "*" not in applies and word not in applies:
                    continue
                detail = {
                    "id": str(raw.get("id") or ""),
                    "word": word,
                    "reading": rd,
                    "writing_common": bool(k.get("common")),
                    "reading_common": bool(kana.get("common")),
                    "writing_tags": [str(x) for x in (k.get("tags") or [])],
                    "reading_tags": [str(x) for x in (kana.get("tags") or [])],
                    "jlpt_waller": str(raw.get("jlpt_waller") or ""),
                    "glosses": glosses[:6],
                    "misc": misc,
                    "info": info,
                    "pos": pos,
                    "dialect": dialect,
                }
                exact[A.exact_key(word, rd)].append(detail)
                by_word[A.normalize_word(word)].append(detail)

        # Kana-only writings are also independent surface forms.
        for kana in kana_items:
            rd = str(kana.get("text") or "").strip()
            applies = kana.get("appliesToKanji") or []
            if applies and applies != ["*"]:
                continue
            detail = {
                "id": str(raw.get("id") or ""),
                "word": rd,
                "reading": rd,
                "writing_common": bool(kana.get("common")),
                "reading_common": bool(kana.get("common")),
                "writing_tags": [str(x) for x in (kana.get("tags") or [])],
                "reading_tags": [str(x) for x in (kana.get("tags") or [])],
                "jlpt_waller": str(raw.get("jlpt_waller") or ""),
                "glosses": glosses[:6],
                "misc": misc,
                "info": info,
                "pos": pos,
                "dialect": dialect,
            }
            exact[A.exact_key(rd, rd)].append(detail)
            by_word[A.normalize_word(rd)].append(detail)

    return exact, by_word, tags_map, source_url


def expand_tags(values: list[str], tags_map: dict) -> list[str]:
    out = []
    for x in values:
        desc = tags_map.get(x)
        out.append(f"{x}:{desc}" if desc else x)
    return out


def has_flag(text: str, needles: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(n in low for n in needles)


def classify(row: dict, details: list[dict], tags_map: dict) -> dict:
    support = int(row.get("support_count") or 0)
    confidence = "HIGH" if support >= 2 else "SINGLE_SOURCE"
    ctype = row.get("candidate_type") or ""
    relation = row.get("relation_type") or ""

    writing_common = any(d.get("writing_common") for d in details)
    reading_common = any(d.get("reading_common") for d in details)
    jmdict_exact = bool(details)
    waller_levels = sorted({d.get("jlpt_waller") for d in details if d.get("jlpt_waller")})
    glosses = []
    tags = []
    pos = []
    for d in details:
        glosses.extend(d.get("glosses") or [])
        tags.extend(expand_tags(d.get("writing_tags") or [], tags_map))
        tags.extend(expand_tags(d.get("reading_tags") or [], tags_map))
        tags.extend(expand_tags(d.get("misc") or [], tags_map))
        tags.extend(expand_tags(d.get("dialect") or [], tags_map))
        pos.extend(expand_tags(d.get("pos") or [], tags_map))
        tags.extend(str(x) for x in (d.get("info") or []))
    tag_text = " | ".join(sorted(set(tags)))

    archaic = has_flag(tag_text, ("archaic", "obsolete", "dated term", "historical term", "arch", "obs"))
    rare = has_flag(tag_text, ("rare term", "rarely", "rare kanji", "rare", "obscure"))
    dialect = has_flag(tag_text, ("dialect", "kansai", "kyoto", "osaka", "touhoku", "tsugaru", "rkb", "ksb"))

    level_consensus = row.get("consensus_level") or ""
    level_conflict = bool(waller_levels and level_consensus and level_consensus not in waller_levels)

    if ctype == "fixed-expression/conjugated":
        decision = "SEPARATE_EXPRESSION_REVIEW"
        priority = "P3"
        reason = "Reference item is a fixed expression/conjugated form; useful for learning but should not be blindly mixed into base-form vocabulary."
    elif not jmdict_exact:
        decision = "MANUAL_VERIFY_SOURCE"
        priority = "P2" if confidence == "HIGH" else "P4"
        reason = "Exact written-form + reading was not resolved in the JMdict common/JLPT subset; verify source spelling and lexical status before adding."
    elif archaic:
        decision = "LOW_PRIORITY_ARCHAIC"
        priority = "P4"
        reason = "Exact form exists but carries archaic/obsolete/historical metadata; keep only if advanced/historical coverage is desired."
    elif rare or dialect:
        decision = "LOW_PRIORITY_RARE_VARIANT"
        priority = "P4" if confidence == "SINGLE_SOURCE" else "P3"
        reason = "Exact form exists but is rare/dialectal/obscure; valid form, lower study priority."
    elif confidence == "HIGH" and (writing_common or reading_common):
        decision = "ADD_HIGH_CONFIDENCE"
        priority = "P1"
        reason = "Supported by >=2 independent reference families and exact JMdict form is common."
    elif confidence == "HIGH" and "same-jmdict-entry" in relation:
        decision = "ADD_DISTINCT_VARIANT"
        priority = "P2"
        reason = "Supported by >=2 families; exact form is a distinct reference-listed writing even though another form of the same JMdict entry already exists."
    elif confidence == "HIGH":
        decision = "ADD_HIGH_CONFIDENCE"
        priority = "P2"
        reason = "Supported by >=2 independent reference families and exact JMdict form exists."
    elif writing_common or reading_common:
        decision = "ADD_AFTER_SOURCE_CHECK"
        priority = "P2"
        reason = "Only one external family supports the JLPT listing, but exact JMdict form is common; suitable after source/level check."
    elif "same-jmdict-entry" in relation:
        decision = "ADD_VARIANT_AFTER_SOURCE_CHECK"
        priority = "P3"
        reason = "Valid exact JMdict variant but only one external reference family supports this JLPT listing."
    else:
        decision = "MANUAL_LEVEL_AND_USAGE_REVIEW"
        priority = "P3"
        reason = "Exact JMdict form exists, but evidence is single-source and form is not marked common."

    if level_conflict and decision.startswith("ADD"):
        reason += " JLPT level conflicts with JMdict/Waller enrichment; add the form but review level before publishing."

    return {
        "evidence_confidence": confidence,
        "jmdict_exact_form_reading": "yes" if jmdict_exact else "no",
        "jmdict_writing_common": "yes" if writing_common else "no",
        "jmdict_reading_common": "yes" if reading_common else "no",
        "jmdict_waller_levels": "|".join(waller_levels),
        "level_conflict_with_jmdict_waller": "yes" if level_conflict else "no",
        "jmdict_tags": tag_text[:2500],
        "jmdict_pos": "|".join(sorted(set(pos)))[:1200],
        "jmdict_gloss": "; ".join(dict.fromkeys(glosses))[:1500],
        "quality_decision": decision,
        "priority": priority,
        "quality_reason": reason,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="audit/vocab/results")
    args = p.parse_args()
    out = Path(args.results)
    if not out.is_absolute():
        out = ROOT / out

    high_path = out / "missing_surface_high_confidence.csv"
    single_path = out / "missing_surface_single_source.csv"
    if not high_path.exists() or not single_path.exists():
        raise SystemExit("Strict surface-form audit outputs are missing")

    exact, _, tags_map, jmdict_url = load_jmdict_details()
    rows = []
    for source_path in (high_path, single_path):
        for row in read_csv(source_path):
            details = exact.get(A.exact_key(row.get("word") or "", row.get("reading") or ""), [])
            rows.append({**row, **classify(row, details, tags_map)})

    priority_order = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
    level_order = {lv: i for i, lv in enumerate(A.LEVELS)}
    rows.sort(key=lambda r: (priority_order.get(r.get("priority"), 9), level_order.get(r.get("consensus_level"), 99), A.normalize_reading(r.get("reading") or ""), A.normalize_word(r.get("word") or "")))

    decisions = Counter(r["quality_decision"] for r in rows)
    priorities = Counter(r["priority"] for r in rows)
    by_level = Counter(r.get("consensus_level") or "Unknown" for r in rows)
    high_rows = [r for r in rows if r["evidence_confidence"] == "HIGH"]
    single_rows = [r for r in rows if r["evidence_confidence"] == "SINGLE_SOURCE"]
    recommended = [r for r in rows if r["quality_decision"].startswith("ADD")]
    manual = [r for r in rows if not r["quality_decision"].startswith("ADD")]

    summary = {
        "review_rule": "Every exact written-form + reading pair reviewed independently; related forms never count as coverage.",
        "jmdict_source": jmdict_url,
        "reviewed_all_missing": len(rows),
        "reviewed_high_confidence": len(high_rows),
        "reviewed_single_source": len(single_rows),
        "recommended_add_or_add_after_check": len(recommended),
        "manual_or_low_priority": len(manual),
        "decision_counts": dict(sorted(decisions.items())),
        "priority_counts": dict(sorted(priorities.items())),
        "reviewed_by_level": {lv: by_level.get(lv, 0) for lv in A.LEVELS},
    }
    (out / "quality_review_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    base_cols = [
        "word","reading","consensus_level","level_votes","family_level_votes","reference_sources",
        "reference_families","support_count","candidate_type","example_meaning","relation_type",
        "same_reading_current_forms","same_word_current_readings","jmdict_current_forms",
        "jmdict_current_readings","jmdict_current_levels","jmdict_all_forms","jmdict_resolved",
    ]
    review_cols = base_cols + [
        "evidence_confidence","jmdict_exact_form_reading","jmdict_writing_common","jmdict_reading_common",
        "jmdict_waller_levels","level_conflict_with_jmdict_waller","jmdict_tags","jmdict_pos","jmdict_gloss",
        "quality_decision","priority","quality_reason",
    ]
    write_csv(out / "final_quality_review_all_missing.csv", rows, review_cols)
    write_csv(out / "quality_review_recommended_add.csv", recommended, review_cols)
    write_csv(out / "quality_review_manual_or_low_priority.csv", manual, review_cols)

    md = [
        "# Final Quality Review — Strict Missing Vocabulary Forms",
        "",
        "Every missing written-form + reading pair was reviewed independently. A related word with the same reading or JMdict entry does **not** remove it.",
        "",
        f"- All missing forms reviewed: **{len(rows):,}**",
        f"- High-confidence (>=2 independent reference families): **{len(high_rows):,}**",
        f"- Single-source: **{len(single_rows):,}**",
        f"- Recommended ADD / ADD-after-check: **{len(recommended):,}**",
        f"- Manual / low-priority / expression review: **{len(manual):,}**",
        "",
        "## Decisions",
        "",
        "| Decision | Count |",
        "|---|---:|",
    ]
    for k, v in sorted(decisions.items()):
        md.append(f"| {k} | {v:,} |")
    md += ["", "## Priority", "", "| Priority | Count |", "|---|---:|"]
    for k, v in sorted(priorities.items()):
        md.append(f"| {k} | {v:,} |")
    md += [
        "",
        "## Important rule",
        "",
        "`ADD_DISTINCT_VARIANT` explicitly covers cases such as 川/河 or 温まる/暖まる: both surface forms are retained as separate learnable entries when the missing form is source-supported.",
        "",
        "`final_quality_review_all_missing.csv` is the complete reviewed queue. No vocabulary data is modified by this review.",
        "",
    ]
    (out / "QUALITY_REVIEW.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
