#!/usr/bin/env python3
"""Load explicit per-exact-key teacher sign-offs from a review ledger.

The ledger is intentionally separate from external cross-check data.  A row only
becomes authoritative when decision=confirmed, so partial human review can be
committed and resumed without pretending the whole C queue has been checked.
"""
from __future__ import annotations

import csv
from pathlib import Path

import recalibrate_jlpt_teacher_v4 as v4

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "jlpt_teacher_manual_review.tsv"
VALID = {"N1", "N2", "N3", "N4", "N5"}


def load_confirmed() -> dict[str, str]:
    if not LEDGER.exists():
        return {}
    out: dict[str, str] = {}
    with LEDGER.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row.get("decision") != "confirmed":
                continue
            reading = (row.get("reading") or "").strip()
            display = (row.get("display") or "").strip()
            level = (row.get("confirmed_level") or "").strip()
            if not reading or not display or level not in VALID:
                raise RuntimeError(f"invalid confirmed teacher-review row: {row}")
            key = f"{reading}|{display}"
            old = out.get(key)
            if old and old != level:
                raise RuntimeError(f"conflicting teacher-review levels for {key}: {old} vs {level}")
            out[key] = level
    return out


def install() -> None:
    original = v4.v1.load_manual_secondary
    if getattr(original, "_teacher_manual_review_wrapped", False):
        return

    def wrapped() -> dict[str, str]:
        out = dict(original())
        out.update(load_confirmed())
        return out

    wrapped._teacher_manual_review_wrapped = True  # type: ignore[attr-defined]
    v4.v1.load_manual_secondary = wrapped
