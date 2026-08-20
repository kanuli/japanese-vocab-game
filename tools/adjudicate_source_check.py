#!/usr/bin/env python3
"""Adjudicate the 378 single-family source-check vocabulary candidates.

Coverage remains strict: exact written-form + reading is the unit. A JLPT level
conflict does not suppress a valid surface form; the selected level is retained
as an estimated, source-backed learning band. Rows are held only when the exact
form is not JMdict-verified or when the source sense is materially ambiguous.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DECISIONS = {"ADD_AFTER_SOURCE_CHECK", "ADD_VARIANT_AFTER_SOURCE_CHECK"}
EXPECTED = 378

# These are sense disambiguations, not coverage aliases. The exact forms remain
# separate vocabulary items; the override only pins the intended learning sense.
SENSE_OVERRIDES = {
    "せっけん|せっけん": "肥皂",
    "しいん|しいん": "寂靜無聲；鴉雀無聲",
    "おおい|おおい": "喂！；喂喂！（呼喊用）",
    "たれ|たれ": "～鬼；～傢伙（帶貶義的人稱後綴）",
    "やかん|やかん": "水壺；燒水壺",
    "ちょうだい|ちょうだい": "給我；請給我",
    "さい|歳": "歲（年齡計數詞）",
    "かげつ|ヶ月": "個月（月數計數詞）",
}

# The source itself is unresolved here (the review row literally carries a TODO
# that conflicts with another lexical sense), so it must not be published.
HOLD = {
    "いえ|いえ": "source-sense-unresolved: source says TODO/same-as-いいえ while the exact form also represents house/no senses",
}

BAD_SOURCE_MARKERS = ("todo", "#name?", "same as ?")


def read_rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def key(row: dict) -> str:
    return f"{str(row.get('reading') or '').strip()}|{str(row.get('word') or '').strip()}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="audit/vocab/results/final_quality_review_all_missing.csv")
    p.add_argument("--results", default="audit/vocab/results")
    args = p.parse_args()
    src = ROOT / args.input
    out = ROOT / args.results
    rows = [r for r in read_rows(src) if (r.get("quality_decision") or "") in SOURCE_DECISIONS]
    if len(rows) != EXPECTED:
        raise SystemExit(f"source-check queue drift: expected {EXPECTED}, found {len(rows)}")

    reviewed = []
    counts = Counter()
    for r in rows:
        k = key(r)
        exact = (r.get("jmdict_exact_form_reading") or "").lower() == "yes"
        resolved = (r.get("jmdict_resolved") or "").lower() == "yes"
        source_meaning = str(r.get("example_meaning") or "").strip()
        gloss = str(r.get("jmdict_gloss") or "").strip()
        lower = source_meaning.lower()

        decision = "APPROVE_SOURCE_CHECK"
        reason = "exact JMdict form+reading verified; external JLPT family supports listing; level retained as estimated source-backed band"
        pinned_tc = SENSE_OVERRIDES.get(k, "")

        if k in HOLD:
            decision = "HOLD_AMBIGUOUS_SOURCE_SENSE"
            reason = HOLD[k]
        elif not exact or not resolved:
            decision = "HOLD_EXACT_FORM_NOT_VERIFIED"
            reason = "exact written-form + reading is not fully JMdict-verified"
        elif any(x in lower for x in BAD_SOURCE_MARKERS) and not pinned_tc:
            decision = "HOLD_MALFORMED_SOURCE_MEANING"
            reason = "source meaning contains an unresolved placeholder; do not publish automatically"
        elif not source_meaning and not gloss:
            decision = "HOLD_NO_SENSE_EVIDENCE"
            reason = "no usable source or JMdict sense text"
        elif (r.get("quality_decision") or "") == "ADD_VARIANT_AFTER_SOURCE_CHECK":
            decision = "APPROVE_DISTINCT_VARIANT_SOURCE_CHECK"
            reason = "exact JMdict variant verified; one external family supports the JLPT listing; keep as independent learnable surface form"

        reviewed.append({
            **r,
            "source_check_decision": decision,
            "source_check_reason": reason,
            "pinned_tc_meaning": pinned_tc,
            "publish_level": r.get("consensus_level") or "N1",
            "level_status": "estimated-conflict" if (r.get("level_conflict_with_jmdict_waller") or "").lower() == "yes" else "estimated-source-backed",
        })
        counts[decision] += 1

    fields = list(reviewed[0].keys())
    approved = [r for r in reviewed if r["source_check_decision"].startswith("APPROVE")]
    held = [r for r in reviewed if r["source_check_decision"].startswith("HOLD")]
    write_csv(out / "source_check_adjudication_all.csv", reviewed, fields)
    write_csv(out / "source_check_approved.csv", approved, fields)
    write_csv(out / "source_check_held.csv", held, fields)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_rule": "exact written-form + reading only",
        "input_source_check_candidates": len(rows),
        "approved": len(approved),
        "held": len(held),
        "decision_counts": dict(sorted(counts.items())),
        "level_policy": "source consensus retained as estimated; level conflict is annotated, not used to suppress a valid exact form",
        "sense_policy": "source meaning + exact JMdict sense; known homograph/homophone ambiguities are pinned or held explicitly",
    }
    (out / "source_check_adjudication_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
