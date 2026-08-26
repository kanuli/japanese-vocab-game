#!/usr/bin/env python3
"""Blocking regression checks for known vocabulary semantic failures."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data" / "vocab_core_verified.js"
ADV = ROOT / "data" / "advanced_vocab.js"


def extract_rows(path: Path, marker: str) -> list[list]:
    text = path.read_text(encoding="utf-8")
    if "天邊一朵雲" in text:
        raise AssertionError(f"forbidden corrupted meaning remains in {path.name}: 天邊一朵雲")
    if marker == "core":
        m = re.search(r"const M=.*?,T=(\[.*?\]),map=new Map", text, flags=re.S)
    else:
        m = re.search(r"const M=.*?,T=(\[.*?\]);\nwindow\.ADVANCED_WORDS", text, flags=re.S)
    if not m:
        raise AssertionError(f"unable to parse {path.name}")
    return json.loads(m.group(1))


def main() -> int:
    core = extract_rows(CORE, "core")
    adv = extract_rows(ADV, "advanced")

    # Core rows: [reading, display, level, meaning, meaningSource, levelSource, entryId]
    # Advanced rows: [level, reading, kanji, meaning, pos]
    all_entries: list[tuple[str, str, str, str]] = []
    for row in core:
        if len(row) >= 4:
            all_entries.append((str(row[0]), str(row[1]), str(row[2]), str(row[3])))
    for row in adv:
        if len(row) >= 4:
            reading, display = str(row[1]), str(row[2] or row[1])
            all_entries.append((reading, display, str(row[0]), str(row[3])))

    by_key: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for reading, display, level, meaning in all_entries:
        by_key.setdefault((reading, display), []).append((level, meaning))

    # User-reported catastrophic mismatch: 西瓜 must mean watermelon, never unrelated prose.
    suika = by_key.get(("すいか", "西瓜"), [])
    assert suika, "missing sentinel entry: 西瓜|すいか"
    assert all("西瓜" in meaning and "天邊一朵雲" not in meaning for _level, meaning in suika), suika

    expected_mai = {
        ("まい", "まい"): ("N2", ("不會", "不打算", "恐怕不")),
        ("まい", "舞"): ("N2", ("舞",)),
        ("まい", "枚"): ("N5", ("張", "枚")),
        ("まい", "毎"): ("N5", ("每",)),
    }
    for key, (level, terms) in expected_mai.items():
        rows = by_key.get(key, [])
        assert rows, f"missing sentinel entry: {key}"
        assert any(lv == level and all(term in meaning for term in terms) for lv, meaning in rows), {key: rows}

    # Previously observed source-noise regressions must stay absent.
    for reading, display, _level, meaning in all_entries:
        if display == "教え":
            assert "學園" not in meaning and "學校" not in meaning and "学校" not in meaning, (reading, display, meaning)
        if display == "共和":
            assert "西周" not in meaning, (reading, display, meaning)
        if display == "指令":
            assert meaning.strip() != "歐洲聯盟指令", (reading, display, meaning)

    print("semantic sentinels passed")
    print("西瓜|すいか:", suika)
    for key in expected_mai:
        print(f"{key[1]}|{key[0]}:", by_key.get(key))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
