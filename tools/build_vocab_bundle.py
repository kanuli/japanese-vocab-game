#!/usr/bin/env python3
"""Build a compact pre-generated advanced vocabulary bundle for the browser game."""
from __future__ import annotations

import csv
import html
import io
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from opencc import OpenCC
except Exception as exc:
    raise SystemExit("opencc-python-reimplemented is required") from exc

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "advanced_vocab.js"
URLS = {
    "core": "https://raw.githubusercontent.com/5mdld/anki-jlpt-decks/main/deck-source/notes.csv",
    "words": "https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/core/words.json",
    "frequency": "https://raw.githubusercontent.com/jkindrix/japanese-language-data/main/data/enrichment/frequency-subtitles.json",
    "thesaurus": "https://raw.githubusercontent.com/lxl66566/Japanese-Chinese-thesaurus/main/final.json",
    "wikidict": "https://raw.githubusercontent.com/open-dict-data/wikidict-zh/master/data/ja-zh_wiki.txt",
}
KANA_RE = re.compile(r"^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$")
JAPANESE_RE = re.compile(r"^[ぁ-ゖァ-ヺ\u3400-\u9fff々〆ヵヶー・]+$")
CJK_RE = re.compile(r"[\u3400-\u9fff々]")
BAD_TAGS = {"arch", "obs", "rare", "dated", "person", "place", "company", "product", "organization", "surname", "given", "n-pr", "X", "sk", "sK", "rk", "rK", "ok", "oK"}


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "japanese-vocab-game-builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str):
    return json.loads(fetch_text(url))


def clean_text(value) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"\[sound:[^\]]+\]", " ", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def reading_from_furigana(value: str, word: str) -> str:
    text = clean_text(value or word).replace(" ", "")
    text = re.sub(r"[\u3400-\u9fff々〆ヵヶ]+\[([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    if KANA_RE.fullmatch(text):
        return text
    return word if KANA_RE.fullmatch(word or "") else ""


def core_keys(text: str) -> set[str]:
    first = (text.splitlines()[:1] or [""])[0].strip().lower()
    delimiter = "," if first == "#separator:comma" else ";" if first == "#separator:semicolon" else "\t"
    keys: set[str] = set()
    for row in csv.reader(io.StringIO(text), delimiter=delimiter):
        if not row or str(row[0] or "").strip().startswith("#"):
            continue
        if len(row) == 40:
            row = row[1:]
        elif len(row) == 38:
            row = [""] + row
        if len(row) != 39:
            continue
        word = clean_text(row[3]).replace(" ", "")
        rd = reading_from_furigana(row[6], word)
        if word and rd:
            keys.add(f"{rd}|{word}")
    return keys


def usable_senses(raw: dict) -> list[dict]:
    senses = []
    for sense in raw.get("sense") or []:
        tags = list(sense.get("misc") or []) + list(sense.get("partOfSpeech") or [])
        if any(tag in BAD_TAGS for tag in tags):
            continue
        senses.append(sense)
    return senses


def choose_entry(raw: dict):
    senses = usable_senses(raw)
    if not senses:
        return None
    kanji = [x for x in (raw.get("kanji") or []) if not any(t in BAD_TAGS for t in (x.get("tags") or []))]
    kana = [x for x in (raw.get("kana") or []) if not any(t in BAD_TAGS for t in (x.get("tags") or []))]
    if not kana:
        return None
    k = next((x for x in kanji if x.get("common")), kanji[0] if kanji else None)
    written = str((k or {}).get("text") or "").strip()
    matching = []
    for item in kana:
        applies = item.get("appliesToKanji") or []
        if not written or not applies or "*" in applies or written in applies:
            matching.append(item)
    if not matching:
        matching = kana
    r = next((x for x in matching if x.get("common")), matching[0])
    rd = str(r.get("text") or "").strip()
    display = written or rd
    if not KANA_RE.fullmatch(rd) or not JAPANESE_RE.fullmatch(display) or len(display) > 22:
        return None
    forms: list[str] = []
    for value in [display, *[x.get("text") for x in kanji], *[x.get("text") for x in kana]]:
        value = str(value or "").strip()
        if value and JAPANESE_RE.fullmatch(value) and value not in forms:
            forms.append(value)
    pos_tags = [tag for sense in senses for tag in (sense.get("partOfSpeech") or [])]
    pos = "other"
    if any(str(tag).startswith("v") or str(tag).startswith("vs") for tag in pos_tags):
        pos = "verb"
    elif any(str(tag).startswith("adj") for tag in pos_tags):
        pos = "adj"
    elif any(str(tag).startswith("adv") for tag in pos_tags):
        pos = "adv"
    elif any(str(tag).startswith("n") for tag in pos_tags):
        pos = "noun"
    elif "conj" in pos_tags:
        pos = "conj"
    elif "prt" in pos_tags:
        pos = "particle"
    return {"raw": raw, "reading": rd, "display": display, "kanji": display if CJK_RE.search(display) else "", "forms": forms[:8], "pos": pos}


def clean_meaning(value, converter: OpenCC) -> str:
    text = clean_text(value)
    text = re.sub(r"^\([^)]{1,30}\)\s*", "", text)
    text = re.sub(r"^(?:名詞|名词|動詞|动词|形容詞|形容词|副詞|副词|名|動|动)\s*", "", text)
    text = converter.convert(text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > 90 or not CJK_RE.search(text):
        return ""
    if re.search(r"[＋+\[\]{}]", text):
        return ""
    if re.search(r"表示.{0,6}(?:句型|文法|語法)|前接|後接", text):
        return ""
    parts = [x.strip() for x in re.split(r"[。；;]", text) if x.strip()]
    return "；".join(parts[:2])[:75]


def load_meanings(wanted: set[str], converter: OpenCC) -> tuple[dict[str, str], dict[str, int]]:
    meanings: dict[str, str] = {}
    stats = {"thesaurus": 0, "wikidict": 0}
    thesaurus = fetch_json(URLS["thesaurus"])
    for jp, zh in (thesaurus or {}).items():
        key = str(jp or "").strip()
        if key not in wanted or key in meanings:
            continue
        value = clean_meaning(zh, converter)
        if value:
            meanings[key] = value
            stats["thesaurus"] += 1
    wiki = fetch_text(URLS["wikidict"])
    for line in wiki.splitlines():
        if not line or line.startswith("#") or "\t" not in line:
            continue
        jp, zh = line.split("\t", 1)
        key = jp.strip()
        candidates = [key]
        paren = re.match(r"^(.+?)\s*[（(][^）)]{1,40}[）)]$", key)
        if paren:
            candidates.append(paren.group(1).strip())
        for candidate in candidates:
            if candidate not in wanted or candidate in meanings:
                continue
            value = clean_meaning(zh, converter)
            if value:
                meanings[candidate] = value
                stats["wikidict"] += 1
                break
    return meanings, stats


def frequency_map(data) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in (data or {}).get("entries") or []:
        text = str(row.get("text") or "").strip()
        if not text:
            continue
        try:
            rank = int(row.get("rank") or 999999)
        except (TypeError, ValueError):
            rank = 999999
        result[text] = min(result.get(text, 999999), rank)
        reading = str(row.get("reading") or "").strip()
        if reading:
            key = f"{text}|{reading}"
            result[key] = min(result.get(key, 999999), rank)
    return result


def best_rank(entry: dict, frequency: dict[str, int]) -> int:
    rank = 999999
    for form in entry["forms"]:
        rank = min(rank, frequency.get(f"{form}|{entry['reading']}", 999999), frequency.get(form, 999999))
    return rank


def level_for(entry: dict, rank: int) -> str:
    waller = entry["raw"].get("jlpt_waller")
    if waller in {"N1", "N2", "N3", "N4", "N5"}:
        return waller
    if rank <= 1200:
        return "N5"
    if rank <= 3000:
        return "N4"
    if rank <= 5500:
        return "N3"
    if rank <= 8000:
        return "N2"
    return "N1"


def quality_key(item: dict):
    waller_priority = 0 if item["waller"] in {"N1", "N2", "N3", "N4", "N5"} else 1
    known_frequency = 0 if item["rank"] < 999999 else 1
    return (waller_priority, known_frequency, item["rank"], len(item["meaning"]), item["reading"])


def main() -> int:
    print("Downloading source datasets...")
    core_text = fetch_text(URLS["core"])
    words_data = fetch_json(URLS["words"])
    try:
        freq_data = fetch_json(URLS["frequency"])
    except Exception as exc:
        print(f"warning: frequency source unavailable: {exc}", file=sys.stderr)
        freq_data = {"entries": []}
    core = core_keys(core_text)
    frequency = frequency_map(freq_data)
    converter = OpenCC("s2hk")
    entries = []
    wanted: set[str] = set()
    for raw in words_data.get("words") or []:
        entry = choose_entry(raw)
        if not entry:
            continue
        key = f"{entry['reading']}|{entry['display']}"
        if key in core:
            continue
        entry["key"] = key
        entries.append(entry)
        wanted.update(entry["forms"])
    print(f"core unique keys: {len(core):,}")
    print(f"eligible common dictionary candidates outside core: {len(entries):,}")
    print(f"Japanese forms requiring a Chinese meaning: {len(wanted):,}")
    meanings, source_stats = load_meanings(wanted, converter)
    print(f"Chinese meanings matched: {len(meanings):,} ({source_stats})")
    candidates: dict[str, dict] = {}
    for entry in entries:
        meaning = next((meanings[f] for f in entry["forms"] if f in meanings), "")
        if not meaning:
            continue
        rank = best_rank(entry, frequency)
        item = {"level": level_for(entry, rank), "reading": entry["reading"], "kanji": entry["kanji"], "meaning": meaning, "pos": entry["pos"], "rank": rank, "waller": entry["raw"].get("jlpt_waller"), "key": entry["key"]}
        previous = candidates.get(entry["key"])
        if previous is None or quality_key(item) < quality_key(previous):
            candidates[entry["key"]] = item
    ranked = sorted(candidates.values(), key=quality_key)
    if len(ranked) > 12500:
        ranked = ranked[:12500]
    merged_unique = len(core | {x["key"] for x in ranked})
    if len(ranked) < 9500 or merged_unique <= 20000:
        raise RuntimeError(f"quality gate failed: generated={len(ranked):,}, merged unique={merged_unique:,}; need >=9,500 generated and >20,000 merged unique")
    counts = Counter(x["level"] for x in ranked)
    tuples = [[x["level"], x["reading"], x["kanji"], x["meaning"], x["pos"]] for x in ranked]
    meta = {
        "version": "prebuilt-20260814-v1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "generatedCount": len(tuples),
        "coreUniqueAtBuild": len(core),
        "mergedUniqueAtBuild": merged_unique,
        "countsByLevel": {level: counts.get(level, 0) for level in ["N1", "N2", "N3", "N4", "N5"]},
        "meaningSources": source_stats,
        "source": "JMdict common (japanese-language-data) + Japanese-Chinese thesaurus + Wikidict ja-zh",
        "levelPolicy": "JLPT Waller when available; otherwise subtitle-frequency estimated N1-N5",
    }
    payload = json.dumps(tuples, ensure_ascii=False, separators=(",", ":"))
    meta_json = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
    js = (
        "// AUTO-GENERATED by tools/build_vocab_bundle.py. Do not edit by hand.\n"
        "// Advanced learning bands are estimated and are not an official JLPT vocabulary list.\n"
        "(()=>{\"use strict\";\n"
        f"const M={meta_json},T={payload};\n"
        "window.ADVANCED_WORDS=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];\n"
        "const base=window.ADVANCED_WORDS.length;\n"
        "for(let i=0;i<T.length;i++){const x=T[i];window.ADVANCED_WORDS.push({id:`bundle-${i}`,level:x[0],reading:x[1],kanji:x[2]||\"\",displayWord:x[2]||x[1],meaning:x[3],pos:x[4]||\"other\",estimated:true,source:\"進階補充詞（預先整理・推定等級）\"});}\n"
        "window.ADVANCED_WORDS_BUNDLE_META={...M,loadedCount:window.ADVANCED_WORDS.length-base};\n"
        "})();\n"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(js, encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024 / 1024:.2f} MiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
