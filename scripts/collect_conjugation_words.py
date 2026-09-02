#!/usr/bin/env python3
"""Collect runtime vocab rows with POS for conjugation enumeration."""
from __future__ import annotations

import csv
import io
import json
import os
import re
import urllib.request
from pathlib import Path

OUT = Path(os.environ.get("CONJ_WORDS_JSON", "word-supertonic3-conj-words.json"))
CSV_PATH = Path(os.environ.get("ANKI_CSV", "notes.csv"))
CSV_URL = os.environ.get(
    "ANKI_CSV_URL",
    "https://raw.githubusercontent.com/5mdld/anki-jlpt-decks/main/deck-source/notes.csv",
)
FIELDS = [
    "Notetype","Deck","NoteID","VocabKanji","VocabPitch","VocabPoS","VocabFurigana",
    "VocabDefSC","VocabDefTC","VocabPlus","VocabAudio","SentType1","SentKanji1",
    "SentFurigana1","SentDefSC1","SentDefTC1","SentAudio1","SentType2","SentKanji2",
    "SentFurigana2","SentDefSC2","SentDefTC2","SentAudio2","SentType3","SentKanji3",
    "SentFurigana3","SentDefSC3","SentDefTC3","SentAudio3","SentType4","SentKanji4",
    "SentFurigana4","SentDefSC4","SentDefTC4","SentAudio4","Sort","Alt1","Alt2","Tags",
]
KANA_RE = re.compile(r"^[\u3041-\u3096\u30a1-\u30fa\u30fc\u30fb\u30fd\u30fe\u309d\u309e]+$")
FURI_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3005\u3006\u30f5\u30f6]+\[([^\]]+)\]")
BR_RE = re.compile(r"\[([^\]]+)\]")


def to_hira(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if 0x30A1 <= o <= 0x30F6:
            out.append(chr(o - 96))
        else:
            out.append(ch)
    return "".join(out)


def reading_of(furi: str, written: str) -> str:
    s = FURI_RE.sub(r"\1", str(furi or written or ""))
    s = BR_RE.sub(r"\1", s)
    s = re.sub(r"\s+", "", s)
    s = to_hira(s)
    if KANA_RE.match(s):
        return s
    w = to_hira(re.sub(r"\s+", "", written or ""))
    return w if KANA_RE.match(w) else ""


def display_kanji(s: str) -> str:
    s = re.sub(r"([\u3400-\u4DBF\u4E00-\u9FFF\u3005\u3006\u30f5\u30f6])\[([^\]]+)\]", r"\1", str(s or ""))
    return re.sub(r"\s+", "", s)


def load_csv() -> str:
    if CSV_PATH.is_file():
        return CSV_PATH.read_text(encoding="utf-8")
    print("Fetching", CSV_URL, flush=True)
    with urllib.request.urlopen(CSV_URL, timeout=120) as r:
        return r.read().decode("utf-8")


def parse(text: str):
    first = text.split("\n", 1)[0].strip().lower()
    delim = "," if first == "#separator:comma" else (";" if first == "#separator:semicolon" else "\t")
    rows = csv.reader(io.StringIO(text), delimiter=delim)
    out = []
    seen = set()
    for row in rows:
        if not row or str(row[0]).startswith("#"):
            continue
        if len(row) == len(FIELDS) + 1:
            row = row[1:]
        if len(row) != len(FIELDS):
            continue
        rec = dict(zip(FIELDS, row))
        written = display_kanji(rec.get("VocabKanji") or "")
        pos = (rec.get("VocabPoS") or "").strip()
        rd = reading_of(rec.get("VocabFurigana") or "", written)
        if not written or not rd or not pos:
            continue
        key = f"{rd}|{written}"
        if key in seen:
            continue
        seen.add(key)
        out.append({"kanji": written, "reading": rd, "pos": pos})
    return out


words = parse(load_csv())
if len(words) < 1000:
    raise SystemExit(f"Unexpectedly few vocab rows: {len(words)}")
OUT.write_text(json.dumps(words, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
print("Wrote", OUT, "rows", len(words))
