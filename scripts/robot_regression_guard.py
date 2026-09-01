#!/usr/bin/env python3
"""Guard against health-validator regressions that can create false site status."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/full-site-health-v3.yml"
LEGACY_WORKFLOW = ROOT / ".github/workflows/site-maintenance.yml"
STATUS_POINTER = ROOT / "maintenance-status.json"
SITE_HEALTH = ROOT / "site-health.js"

failures: list[str] = []
warnings: list[str] = []

if LEGACY_WORKFLOW.exists():
    failures.append("legacy self-invalidating .github/workflows/site-maintenance.yml must remain retired")

if not WORKFLOW.is_file():
    failures.append("missing .github/workflows/full-site-health-v3.yml")
else:
    text = WORKFLOW.read_text(encoding="utf-8")

    # Never hard-pin a page assertion to a cache-buster value. That creates false
    # failures whenever a legitimate JS version token changes.
    pinned = re.findall(r"count\([^\n]*?\.js\?v=[^\n]*?\)", text)
    if pinned:
        failures.append("version-pinned JavaScript validator assertion found: " + " | ".join(pinned[:5]))

    # Any explicit Python required=[...] list must refer only to files that exist.
    for block in re.findall(r"required\s*=\s*\[(.*?)\]", text, flags=re.S):
        for name in re.findall(r"['\"]([^'\"]+)['\"]", block):
            if not (ROOT / name).is_file():
                failures.append(f"stale required-file validator reference: {name}")

    # Real site/runtime resources and validator changes must re-run full-site health.
    expected_triggers = [
        "'*.html'", "'*.js'", "'*.css'", "'data/**'",
        "'scripts/audit_tts_pronunciation.py'",
        "'.github/workflows/full-site-health-v3.yml'",
    ]
    for token in expected_triggers:
        if token not in text:
            failures.append(f"health-v3 push coverage missing {token}")

    # Structural gates that prevent the two incident classes found by Robot/Teacher.
    required_markers = {
        "deployment SHA gate": "Wait for the same revision to be the successful Pages deployment",
        "live Chromium runtime gate": "Browser smoke — live 11 pages",
        "post-live revision gate": "Confirm audited revision is still current after live checks",
        "pronunciation calibration": "python scripts/audit_tts_pronunciation.py --self-test",
        "off-Pages health status": "health-status",
        "transient 5xx retry": "e.transient",
    }
    for label, marker in required_markers.items():
        if marker not in text:
            failures.append(f"health-v3 missing {label}")

    # Dynamic status must never be committed/pushed to main from the health job.
    forbidden = [
        "git add maintenance-status.json",
        "git push origin main",
        "git commit -m \"Update automated site maintenance status\"",
    ]
    for marker in forbidden:
        if marker in text:
            failures.append(f"health-v3 may self-invalidate Pages deployment: {marker}")

# The Pages copy is an immutable pointer; actual dynamic status belongs off main.
if not STATUS_POINTER.is_file():
    failures.append("missing maintenance-status.json pointer")
else:
    pointer = STATUS_POINTER.read_text(encoding="utf-8", errors="replace")
    if '"kind": "maintenance-status-pointer"' not in pointer:
        failures.append("main maintenance-status.json is not a status pointer")
    if 'health-status/maintenance-status.json' not in pointer:
        failures.append("maintenance status pointer does not target health-status branch")

if not SITE_HEALTH.is_file():
    failures.append("missing site-health.js")
else:
    health = SITE_HEALTH.read_text(encoding="utf-8", errors="replace")
    for marker in ["statusUrl", "deploymentAligned", "liveBrowser", "revisionStillCurrent"]:
        if marker not in health:
            failures.append(f"site-health.js missing v3 status gate {marker}")

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
print(
    f"Robot regression guard OK: {len(pages)} HTML pages; health-v3 deployment, "
    "live-browser, pronunciation-calibration and off-Pages-status invariants protected."
)
