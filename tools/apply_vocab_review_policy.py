#!/usr/bin/env python3
"""Apply repo-specific review policy after the generic strict-surface reviewer.

The generic reviewer is intentionally evidence-driven. This overlay applies explicit
source/sense HOLD decisions that were already adjudicated so they do not reappear as
false ADD recommendations on every re-audit.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import audit_vocab_coverage as A

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_hold_map(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for raw_key, reason in (data.get("explicit_holds") or {}).items():
        if "|" not in raw_key:
            continue
        reading, word = raw_key.split("|", 1)
        out[A.exact_key(word, reading)] = str(reason or "explicit source/sense HOLD")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--results", default="audit/vocab/results")
    p.add_argument("--policy", default="data/coverage_sourcecheck_policy.json")
    p.add_argument("--expected-present-holds", type=int, default=None)
    args = p.parse_args()

    out = ROOT / args.results
    policy = ROOT / args.policy
    all_path = out / "final_quality_review_all_missing.csv"
    if not all_path.exists():
        raise SystemExit("Generic quality review output is missing")
    holds = load_hold_map(policy)
    rows = read_csv(all_path)
    if not rows:
        raise SystemExit("Generic quality review output is empty")

    present = 0
    for row in rows:
        key = A.exact_key(row.get("word") or "", row.get("reading") or "")
        if key not in holds:
            continue
        present += 1
        row["quality_decision"] = "MANUAL_VERIFY_SOURCE"
        row["priority"] = "P4"
        row["quality_reason"] = "Explicit source/sense HOLD; do not auto-publish until independently resolved. " + holds[key]

    if args.expected_present_holds is not None and present != args.expected_present_holds:
        raise SystemExit(f"Expected {args.expected_present_holds} explicit HOLD rows in remaining gap set, found {present}")

    decisions = Counter(r.get("quality_decision") or "" for r in rows)
    priorities = Counter(r.get("priority") or "" for r in rows)
    by_level = Counter(r.get("consensus_level") or "Unknown" for r in rows)
    high_rows = [r for r in rows if r.get("evidence_confidence") == "HIGH"]
    single_rows = [r for r in rows if r.get("evidence_confidence") == "SINGLE_SOURCE"]
    recommended = [r for r in rows if str(r.get("quality_decision") or "").startswith("ADD")]
    manual = [r for r in rows if not str(r.get("quality_decision") or "").startswith("ADD")]

    fields = list(rows[0].keys())
    write_csv(all_path, rows, fields)
    write_csv(out / "quality_review_recommended_add.csv", recommended, fields)
    write_csv(out / "quality_review_manual_or_low_priority.csv", manual, fields)

    summary = {
        "review_rule": "Every exact written-form + reading pair reviewed independently; related forms never count as coverage.",
        "policy_overlay": "Explicit source/sense HOLD rows are reclassified as MANUAL_VERIFY_SOURCE and excluded from actionable ADD recommendations.",
        "explicit_hold_rows_reclassified": present,
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

    md = [
        "# Final Quality Review — Strict Missing Vocabulary Forms",
        "",
        "Every missing written-form + reading pair is reviewed independently. Same-reading/JMdict relations never count as coverage.",
        "",
        f"- Remaining strict forms reviewed: **{len(rows):,}**",
        f"- High-confidence: **{len(high_rows):,}**",
        f"- Single-source: **{len(single_rows):,}**",
        f"- Actionable ADD / ADD-after-check: **{len(recommended):,}**",
        f"- Manual / low-priority / expression review: **{len(manual):,}**",
        f"- Explicit source/sense HOLD rows: **{present:,}**",
        "",
        "## Decisions",
        "",
        "| Decision | Count |",
        "|---|---:|",
    ]
    for k, v in sorted(decisions.items()):
        md.append(f"| {k} | {v:,} |")
    md += [
        "",
        "## Policy overlay",
        "",
        "Explicit HOLD entries remain visible as missing exact surface forms, but are deliberately excluded from automatic publish recommendations until their source/sense conflict is independently resolved.",
        "",
    ]
    (out / "QUALITY_REVIEW.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
