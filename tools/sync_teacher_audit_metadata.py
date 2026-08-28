#!/usr/bin/env python3
"""Synchronize teacher-audit metadata with the canonical exact-key TSV.

The TSV is the row-level source of truth after key normalization/deduplication.
This script recomputes structural aggregate metadata instead of preserving stale
snapshot counts.  It intentionally does not make linguistic or JLPT decisions.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TSV = ROOT / "data" / "jlpt_teacher_audit.tsv"
AUDIT = ROOT / "data" / "vocab_audit.json"
VALID_LEVELS = {"N1", "N2", "N3", "N4", "N5"}


def ordered_counts(counter: Counter[str]) -> dict[str, int]:
    return {level: int(counter.get(level, 0)) for level in ("N5", "N4", "N3", "N2", "N1") if counter.get(level, 0)}


def main() -> int:
    with TSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if len(rows) < 32000:
        raise SystemExit(f"teacher TSV unexpectedly small: {len(rows)}")

    keys: list[str] = []
    for i, row in enumerate(rows, start=2):
        reading = (row.get("reading") or "").strip()
        display = (row.get("display") or "").strip()
        level = (row.get("level") or "").strip()
        if not reading or not display:
            raise SystemExit(f"blank exact key at TSV row {i}")
        if level not in VALID_LEVELS:
            raise SystemExit(f"invalid JLPT level at TSV row {i}: {level!r}")
        keys.append(f"{reading}|{display}")

    duplicate_count = len(keys) - len(set(keys))
    if duplicate_count:
        raise SystemExit(f"duplicate exact keys remain in teacher TSV: {duplicate_count}")

    by_level = Counter((r.get("level") or "").strip() for r in rows)
    by_grade = Counter((r.get("grade") or "").strip() for r in rows if (r.get("grade") or "").strip())
    by_basis = Counter((r.get("basis") or "").strip() for r in rows if (r.get("basis") or "").strip())

    estimated = [r for r in rows if (r.get("status") or "").strip().lower().startswith("estimated")]
    direct = [r for r in rows if not (r.get("status") or "").strip().lower().startswith("estimated")]
    estimated_by_level = Counter((r.get("level") or "").strip() for r in estimated)
    direct_by_level = Counter((r.get("level") or "").strip() for r in direct)
    direct_conflicts = sum("conflict" in (r.get("status") or "").strip().lower() for r in rows)
    estimated_n1 = [r for r in estimated if (r.get("level") or "").strip() == "N1"]
    if estimated_n1:
        sample = [f"{r.get('reading')}|{r.get('display')}" for r in estimated_n1[:20]]
        raise SystemExit(f"estimated N1 forbidden; found {len(estimated_n1)}: {sample}")

    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    rec = data.get("jlptRecalibration")
    if not isinstance(rec, dict) or rec.get("status") != "complete":
        raise SystemExit("vocab_audit.json missing complete jlptRecalibration metadata")
    if rec.get("scope") != "every core+advanced runtime word exact key":
        raise SystemExit(f"unexpected teacher audit scope: {rec.get('scope')!r}")

    row_count = len(rows)
    combined = ordered_counts(by_level)
    grades = dict(sorted((k, int(v)) for k, v in by_grade.items()))
    bases = dict(sorted((k, int(v)) for k, v in by_basis.items()))

    rec["rowCount"] = row_count
    rec["combinedCountsByLevel"] = combined
    rec["directCountsByLevel"] = ordered_counts(direct_by_level)
    rec["estimatedCountsByLevel"] = ordered_counts(estimated_by_level)
    rec["teacherGradeCounts"] = grades
    rec["teacherBasisCounts"] = bases
    rec["directRows"] = len(direct)
    rec["estimatedRows"] = len(estimated)
    rec["directConflictRows"] = int(direct_conflicts)
    rec["estimatedN1WithoutRarityEvidence"] = 0
    rec["duplicateExactKeys"] = 0
    rec["canonicalExactKeyCount"] = row_count
    rec["metadataSyncedFrom"] = "data/jlpt_teacher_audit.tsv"

    counts = data.setdefault("counts", {})
    counts["runtimeUnique"] = row_count
    counts["jlptCountsCoreAdvanced"] = combined

    AUDIT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Re-read and assert arithmetic self-consistency before allowing a commit.
    assert sum(combined.values()) == row_count
    assert len(direct) + len(estimated) == row_count
    assert sum(rec["teacherGradeCounts"].values()) == row_count
    assert sum(rec["teacherBasisCounts"].values()) == row_count

    print(json.dumps({
        "rowCount": row_count,
        "combinedCountsByLevel": combined,
        "teacherGradeCounts": grades,
        "teacherBasisCounts": bases,
        "directRows": len(direct),
        "estimatedRows": len(estimated),
        "directConflictRows": direct_conflicts,
        "duplicateExactKeys": duplicate_count,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
