#!/usr/bin/env python3
"""Robust entrypoint for the complete runtime supplement teacher audit."""
from __future__ import annotations

import json
import re
from pathlib import Path

import audit_runtime_supplements as audit
import teacher_jlpt_policy_v5 as v5


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


v5.install()
audit.choose_direct = v5.choose_runtime_direct
audit.parse_r_file = parse_r_file

if __name__ == "__main__":
    raise SystemExit(audit.main())
