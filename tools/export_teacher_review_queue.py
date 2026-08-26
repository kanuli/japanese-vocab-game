#!/usr/bin/env python3
"""Export every teacher-audit conflict row for explicit human/teacher review."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "jlpt_teacher_audit.tsv"
OUT = ROOT / "data" / "jlpt_teacher_review_queue.tsv"
META = ROOT / "data" / "jlpt_teacher_review_queue.json"


def severity(row: dict[str, str]) -> tuple[int, int, str, str]:
    level = row.get("level", "")
    # Prioritize suspicious advanced labels first, then exact-source conflicts.
    advanced = {"N1": 5, "N2": 4, "N3": 3, "N4": 2, "N5": 1}.get(level, 0)
    conflict = 1 if row.get("conflict", "").lower() in {"1", "true", "yes"} else 0
    return (-advanced, -conflict, row.get("reading", ""), row.get("display", ""))


def main() -> int:
    with SRC.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    review = [r for r in rows if r.get("grade") == "C"]
    review.sort(key=severity)
    fields = list(rows[0].keys()) if rows else []
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(review)
    by_level: dict[str, int] = {}
    by_basis: dict[str, int] = {}
    for r in review:
        by_level[r.get("level", "")] = by_level.get(r.get("level", ""), 0) + 1
        by_basis[r.get("basis", "")] = by_basis.get(r.get("basis", ""), 0) + 1
    meta = {
        "status": "complete",
        "sourceRows": len(rows),
        "reviewRows": len(review),
        "countsByLevel": dict(sorted(by_level.items())),
        "countsByBasis": dict(sorted(by_basis.items(), key=lambda kv: (-kv[1], kv[0]))),
        "rule": "all grade-C teacher audit rows; no sampling",
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
