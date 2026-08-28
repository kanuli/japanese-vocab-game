#!/usr/bin/env python3
"""Guard against maintenance-validator regressions that can create false site failures."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/site-maintenance.yml"

failures: list[str] = []
warnings: list[str] = []

if not WORKFLOW.is_file():
    failures.append("missing .github/workflows/site-maintenance.yml")
else:
    text = WORKFLOW.read_text(encoding="utf-8")

    # Today's incident class: an assertion hard-pinned to a cache-buster token.
    pinned = re.findall(r"count\([^\n]*?\.js\?v=[^\n]*?\)", text)
    if pinned:
        failures.append("version-pinned JavaScript validator assertion found: " + " | ".join(pinned[:5]))

    # Any explicit Python required=[...] list must refer only to files that still exist.
    for block in re.findall(r"required\s*=\s*\[(.*?)\]", text, flags=re.S):
        for name in re.findall(r"['\"]([^'\"]+)['\"]", block):
            if not (ROOT / name).is_file():
                failures.append(f"stale required-file validator reference: {name}")

    # Changes to real site resources should trigger maintenance. Status output itself is
    # deliberately excluded to avoid a self-trigger loop.
    expected_triggers = ["'*.html'", "'*.js'", "'*.css'", "'data/**'", "'.github/workflows/site-maintenance.yml'"]
    for token in expected_triggers:
        if token not in text:
            failures.append(f"maintenance push coverage missing {token}")

# Site pages must remain wired into health monitoring exactly once.
pages = sorted(ROOT.glob("*.html"))
if len(pages) < 11:
    failures.append(f"unexpected HTML page count: {len(pages)}")
for page in pages:
    body = page.read_text(encoding="utf-8", errors="replace")
    count = body.count("site-health.js")
    if count != 1:
        failures.append(f"{page.name}: site-health.js count={count}")

if failures:
    for item in failures:
        print("FAIL", item, file=sys.stderr)
    raise SystemExit(1)

for item in warnings:
    print("WARN", item)
print(f"Robot regression guard OK: {len(pages)} HTML pages; validator invariants protected.")
