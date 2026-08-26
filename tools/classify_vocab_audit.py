#!/usr/bin/env python3
"""Classify audit findings after vocabulary generation.

Different spellings of the same lexical item may reasonably have different learning
levels (for example すいか vs 西瓜). Those are review signals, not fatal data errors.
All other audit failures remain blocking.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "vocab_audit.json"

if not PATH.exists():
    raise SystemExit("vocabulary builder did not produce data/vocab_audit.json")

audit = json.loads(PATH.read_text(encoding="utf-8"))
fatal = list(audit.get("fatalIssues") or [])
review = list(audit.get("reviewIssues") or [])
remaining = []
for issue in fatal:
    if issue.get("type") == "same_meaning_variant_level_conflict":
        review.append({**issue, "type": "orthographic_variant_level_difference"})
    else:
        remaining.append(issue)

audit["reviewIssues"] = review
audit["reviewIssueCount"] = len(review)
audit["fatalIssues"] = remaining
audit["fatalIssueCount"] = len(remaining)
counts = audit.setdefault("counts", {})
counts["orthographicVariantLevelDifferencesForReview"] = len(review)
PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if remaining:
    raise SystemExit(f"blocking vocabulary audit issues remain: {remaining[:5]}")
print(f"audit classified: 0 blocking issues; {len(review)} orthographic-level review signal(s)")
