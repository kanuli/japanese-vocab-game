#!/usr/bin/env python3
"""Adjudicate the 378 single-family source-check vocabulary candidates.

Coverage remains strict: exact written-form + reading is the unit. A JLPT level
conflict does not suppress a valid surface form. Traditional-Chinese sense pins
and explicit holds live in data/coverage_sourcecheck_policy.json so the policy
is inspectable and reusable by every build path.
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


def load_policy(path: Path) -> tuple[dict[str, str], dict[str, str], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    pins = {str(k): str(v) for k, v in (data.get("pinned_tc_meanings") or {}).items() if str(k) and str(v)}
    holds = {str(k): str(v) for k, v in (data.get("explicit_holds") or {}).items() if str(k) and str(v)}
    return pins, holds, data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="audit/vocab/results/final_quality_review_all_missing.csv")
    p.add_argument("--results", default="audit/vocab/results")
    p.add_argument("--policy", default="data/coverage_sourcecheck_policy.json")
    args = p.parse_args()
    src = ROOT / args.input
    out = ROOT / args.results
    policy_path = ROOT / args.policy
    pins, holds, policy = load_policy(policy_path)

    rows = [r for r in read_rows(src) if (r.get("quality_decision") or "") in SOURCE_DECISIONS]
    if len(rows) != EXPECTED:
        raise SystemExit(f"source-check queue drift: expected {EXPECTED}, found {len(rows)}")

    reviewed = []
    counts = Counter()
    override_used = 0
    for r in rows:
        k = key(r)
        exact = (r.get("jmdict_exact_form_reading") or "").lower() == "yes"
        resolved = (r.get("jmdict_resolved") or "").lower() == "yes"
        source_meaning = str(r.get("example_meaning") or "").strip()
        gloss = str(r.get("jmdict_gloss") or "").strip()
        lower = source_meaning.lower()

        decision = "APPROVE_SOURCE_CHECK"
        reason = "exact JMdict form+reading verified; external JLPT family supports listing; level retained as estimated source-backed band"
        pinned_tc = pins.get(k, "")
        if pinned_tc:
            override_used += 1

        if k in holds:
            decision = "HOLD_AMBIGUOUS_SOURCE_SENSE"
            reason = holds[k]
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
        if pinned_tc and decision.startswith("APPROVE"):
            reason += "; intended Traditional-Chinese learning sense explicitly pinned after source/JMdict comparison"

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
        "policy_file": str(policy_path.relative_to(ROOT)),
        "policy_version": policy.get("version"),
        "input_source_check_candidates": len(rows),
        "approved": len(approved),
        "held": len(held),
        "pinned_sense_overrides_used": override_used,
        "configured_pinned_sense_overrides": len(pins),
        "configured_explicit_holds": len(holds),
        "decision_counts": dict(sorted(counts.items())),
        "level_policy": policy.get("level_policy"),
        "sense_policy": policy.get("meaning_policy"),
    }
    (out / "source_check_adjudication_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
