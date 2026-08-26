#!/usr/bin/env python3
"""Robust entrypoint for the complete runtime supplement teacher audit."""
from __future__ import annotations

import json
import re
from pathlib import Path

import audit_runtime_supplements as audit
import teacher_jlpt_policy_v5 as v5
import teacher_manual_review as manual_review


def parse_r_file(path: Path) -> list[dict]:
    """Parse generated manual layers regardless of harmless whitespace/minification."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"\bconst\s+R\s*=\s*(\[.*?\])\s*;", text, re.S)
    if not m:
        raise RuntimeError(f"cannot parse {path.name}: missing const R array")
    rows = json.loads(m.group(1))
    out = []
    for x in rows:
        if not isinstance(x, list) or len(x) < 4:
            continue
        level, reading, display, meaning = (str(x[i] or "") for i in range(4))
        if reading and display and meaning and level in audit.VALID:
            out.append({
                "reading": reading,
                "display": display,
                "meaning": meaning,
                "original_level": level,
                "source": path.stem,
            })
    return out


manual_review.install()
v5.install()
audit.choose_direct = v5.choose_runtime_direct
audit.parse_r_file = parse_r_file
_original_write_overlay = audit.write_overlay


def write_overlay_v2(full_rows, supplement_keys, sources):
    meta = _original_write_overlay(full_rows, supplement_keys, sources)
    text = audit.OVERLAY_JS.read_text(encoding="utf-8")
    text = text.replace("20260826-teacher-runtime-v1", v5.RUNTIME_VERSION)
    text = text.replace(
        "apply teacher-audited exact reading+display level after all additive runtime supplements",
        "apply v5 source-lineage-aware teacher level after all additive runtime supplements",
    )
    audit.OVERLAY_JS.write_text(text, encoding="utf-8")
    meta["version"] = v5.RUNTIME_VERSION
    meta["rule"] = "apply v5 source-lineage-aware teacher level after all additive runtime supplements"
    meta["sourceIndependence"] = v5.SOURCE_INDEPENDENCE
    return meta


audit.write_overlay = write_overlay_v2


def main() -> int:
    rc = audit.main()
    data = json.loads(audit.AUDIT_JSON.read_text(encoding="utf-8"))
    runtime = data.get("runtimeTeacherAudit", {})
    runtime["version"] = v5.RUNTIME_VERSION
    runtime["policyRevision"] = "v5-source-lineage"
    runtime["sourceIndependence"] = v5.SOURCE_INDEPENDENCE
    runtime.setdefault("overlay", {})["version"] = v5.RUNTIME_VERSION
    runtime["overlay"]["sourceIndependence"] = v5.SOURCE_INDEPENDENCE
    data["runtimeTeacherAudit"] = runtime
    data.setdefault("policy", {})["runtimeJlptLevel"] = (
        "Every additive runtime exact key is reconciled by v5. OpenJLPT, Waller/Tanos and "
        "unprovenanced Tomoshi JLPT labels are one legacy lineage, not independent votes. "
        "Unsupported estimated N1 is forbidden."
    )
    audit.AUDIT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())