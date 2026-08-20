#!/usr/bin/env python3
"""Validate that every materialized coverage addition survives in the bundle."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import audit_vocab_coverage as A
import apply_coverage_additions as P

ROOT = Path(__file__).resolve().parents[1]
CJK_RE = re.compile(r"[\u3400-\u9fff]")
LEVELS = set(A.LEVELS)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", default="data/advanced_vocab.js")
    p.add_argument("--additions", default="data/coverage_additions.json")
    p.add_argument("--report", default="audit/vocab/results/coverage_additions_validation.json")
    args = p.parse_args()

    bundle = Path(args.bundle)
    additions_path = Path(args.additions)
    report_path = Path(args.report)
    if not bundle.is_absolute():
        bundle = ROOT / bundle
    if not additions_path.is_absolute():
        additions_path = ROOT / additions_path
    if not report_path.is_absolute():
        report_path = ROOT / report_path

    _, tuples = P.parse_bundle(bundle)
    payload = json.loads(additions_path.read_text(encoding="utf-8"))
    additions = payload.get("additions") or []

    bundle_keys = set()
    for row in tuples:
        if not isinstance(row, list) or len(row) < 4:
            continue
        level, reading, written, meaning = row[:4]
        word = str(written or reading or "").strip()
        bundle_keys.add(A.exact_key(word, str(reading or "")))

    missing_from_bundle = []
    invalid_meanings = []
    invalid_levels = []
    duplicate_keys = []
    seen = set()

    for item in additions:
        word = str(item.get("word") or "").strip()
        reading = str(item.get("reading") or "").strip()
        key = A.exact_key(word, reading)
        if key in seen:
            duplicate_keys.append({"word": word, "reading": reading})
        seen.add(key)
        if key not in bundle_keys:
            missing_from_bundle.append({"word": word, "reading": reading})
        meaning = str(item.get("meaning") or "")
        if not meaning or not CJK_RE.search(meaning):
            invalid_meanings.append({"word": word, "reading": reading, "meaning": meaning})
        if str(item.get("level") or "") not in LEVELS:
            invalid_levels.append({"word": word, "reading": reading, "level": item.get("level")})

    report = {
        "materialized_additions": len(additions),
        "unique_addition_keys": len(seen),
        "bundle_unique_keys": len(bundle_keys),
        "missing_from_bundle": missing_from_bundle,
        "invalid_traditional_chinese_meanings": invalid_meanings,
        "invalid_levels": invalid_levels,
        "duplicate_addition_keys": duplicate_keys,
        "passed": not (missing_from_bundle or invalid_meanings or invalid_levels or duplicate_keys),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit("coverage additions validation failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
