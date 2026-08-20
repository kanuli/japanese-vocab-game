#!/usr/bin/env python3
"""Audit JLPT N1-N5 vocabulary coverage against multiple public reference datasets.

This tool intentionally separates:
1) source/core rows,
2) rows that the current browser runtime loader can actually accept,
3) repo-hosted curated/advanced supplements, and
4) external JLPT reference consensus.

It does NOT modify the learning database.
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ("N5", "N4", "N3", "N2", "N1")
CORE_URLS = [
    "https://raw.githubusercontent.com/5mdld/anki-jlpt-decks/main/deck-source/notes.csv",
    "https://cdn.jsdelivr.net/gh/5mdld/anki-jlpt-decks@main/deck-source/notes.csv",
]
SOURCE_FAMILY = {"openjlpt": "waller-derived", "waller": "waller-derived", "wordmaster": "community-independent"}
REFERENCE_URLS = {
    "openjlpt": {
        level: f"https://raw.githubusercontent.com/evanclan/OpenJLPT/main/data/json/vocab/{level.lower()}.json"
        for level in LEVELS
    },
    "waller": {
        level: f"https://raw.githubusercontent.com/stephenmk/yomitan-jlpt-vocab/main/original_data/{level.lower()}.csv"
        for level in LEVELS
    },
    "wordmaster": {
        level: f"https://raw.githubusercontent.com/lratusa/wordmaster-wordlists/main/japanese/jlpt_{level.lower()}.json"
        for level in LEVELS
    },
}
FIELDS = [
    "Notetype","Deck","NoteID","VocabKanji","VocabPitch","VocabPoS","VocabFurigana",
    "VocabDefSC","VocabDefTC","VocabPlus","VocabAudio","SentType1","SentKanji1",
    "SentFurigana1","SentDefSC1","SentDefTC1","SentAudio1","SentType2","SentKanji2",
    "SentFurigana2","SentDefSC2","SentDefTC2","SentAudio2","SentType3","SentKanji3",
    "SentFurigana3","SentDefSC3","SentDefTC3","SentAudio3","SentType4","SentKanji4",
    "SentFurigana4","SentDefSC4","SentDefTC4","SentAudio4","Sort","Alt1","Alt2","Tags",
]
KANA_RE = re.compile(r"^[ぁ-ゖァ-ヺー・ヽヾゝゞ]+$")
KANJI_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF々〆ヵヶ]")
LEVEL_RE = re.compile(r"(?:^|[^A-Za-z0-9])N([1-5])(?=$|[^0-9])", re.I)
TAG_RE = re.compile(r"<[^>]+>")
SOUND_RE = re.compile(r"\[sound:[^\]]+\]", re.I)
SMALL_KANA_TRANS = str.maketrans({
    "ぁ":"あ","ぃ":"い","ぅ":"う","ぇ":"え","ぉ":"お",
    "ゃ":"や","ゅ":"ゆ","ょ":"よ","っ":"つ","ゎ":"わ",
    "ァ":"ア","ィ":"イ","ゥ":"ウ","ェ":"エ","ォ":"オ",
    "ャ":"ヤ","ュ":"ユ","ョ":"ヨ","ッ":"ツ","ヮ":"ワ",
})


@dataclass(frozen=True)
class Entry:
    source: str
    level: str
    word: str
    reading: str
    meaning: str = ""
    note: str = ""

    @property
    def exact_key(self) -> str:
        return exact_key(self.word, self.reading)

    @property
    def variant_key(self) -> str:
        return variant_key(self.word, self.reading)


def http_text(url: str, timeout: int = 120) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "japanese-vocab-game-coverage-audit/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def first_text(urls: Iterable[str]) -> tuple[str, str]:
    errors = []
    for url in urls:
        try:
            return http_text(url), url
        except Exception as exc:  # network variability is expected in CI
            errors.append(f"{url}: {exc}")
    raise RuntimeError("all source mirrors failed: " + " | ".join(errors))


def clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = SOUND_RE.sub(" ", text)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def nfkc(value: str) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def kata_to_hira(value: str) -> str:
    out = []
    for ch in nfkc(value):
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def normalize_reading(value: str) -> str:
    return kata_to_hira(value).replace(" ", "").replace("・", "")


def normalize_word(value: str) -> str:
    return nfkc(value).replace(" ", "").replace("・", "")


def loose_kana(value: str) -> str:
    return kata_to_hira(nfkc(value)).translate(SMALL_KANA_TRANS).replace(" ", "").replace("・", "").replace("ー", "")


def loose_word(value: str) -> str:
    # Conservative kana normalization for spelling variants.
    return loose_kana(normalize_word(value))


def kanji_skeleton(value: str) -> str:
    """Keep CJK characters only; useful for okurigana variants such as 打合せ/打ち合わせ."""
    return "".join(ch for ch in nfkc(value) if "\u3400" <= ch <= "\u9fff" or ch in "々〆ヵヶ")


def loose_kanji_skeleton(value: str) -> str:
    # 御 is frequently written as お/ご in everyday orthography (御飯/ご飯).
    return kanji_skeleton(value).replace("御", "")


def exact_key(word: str, reading: str) -> str:
    return f"{normalize_reading(reading)}|{normalize_word(word)}"


def variant_key(word: str, reading: str) -> str:
    return f"{loose_kana(reading)}|{loose_word(word)}"


def reading_aliases(word: str, reading: str) -> list[str]:
    """Return conservative reading aliases used only for coverage matching."""
    base = loose_kana(reading)
    aliases = [base] if base else []
    # Some JLPT datasets encode verbalized nouns as 案内 / あんないする.
    # Do not strip する when the written form itself is 愛する-like.
    surface = normalize_word(word)
    if base.endswith("する") and not surface.endswith("する"):
        aliases.append(base[:-2])
    return list(dict.fromkeys(x for x in aliases if x))


def candidate_type(word: str, reading: str) -> str:
    r = normalize_reading(reading)
    if any(r.endswith(x) for x in ("ください", "なさい", "ません", "ましょう", "ございます", "でした")):
        return "fixed-expression/conjugated"
    if r.endswith("ます") and len(r) > 4:
        return "fixed-expression/conjugated"
    if is_kana(word):
        return "kana/loanword"
    return "lexical"


def is_kana(value: str) -> bool:
    return bool(value) and bool(KANA_RE.fullmatch(nfkc(value).replace(" ", "")))


def reading_from_furigana(value: str, word: str) -> str:
    text = clean_text(value or word).replace(" ", "")
    text = re.sub(r"[\u3400-\u9fff々〆ヵヶ]+\[([^\]]+)\]", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]", r"\1", text)
    if is_kana(text):
        return text
    return word if is_kana(word) else ""


def csv_rows(text: str) -> list[list[str]]:
    first = (text.splitlines()[:1] or [""])[0].strip().lower()
    delimiter = "," if first == "#separator:comma" else ";" if first == "#separator:semicolon" else "\t"
    return list(csv.reader(io.StringIO(text), delimiter=delimiter))


def robust_row(row: list[str]) -> tuple[list[str] | None, str]:
    if len(row) == 40:
        return row[1:], "40->39"
    if len(row) == 39:
        return row, "39"
    if len(row) == 38:
        return ["", *row], "38->39"
    return None, f"unsupported-width:{len(row)}"


def runtime_row(row: list[str]) -> tuple[list[str] | None, str]:
    # Mirrors wordaudio-data.js today: 40 -> slice first, 39 accepted, 38 rejected.
    if len(row) == 40:
        return row[1:], "40->39"
    if len(row) == 39:
        return row, "39"
    return None, f"runtime-width-reject:{len(row)}"


def row_to_fields(row: list[str]) -> dict[str, str]:
    return {name: (row[i] if i < len(row) else "") for i, name in enumerate(FIELDS)}


def parse_core(text: str) -> tuple[list[Entry], list[Entry], list[dict]]:
    source_entries: list[Entry] = []
    runtime_entries: list[Entry] = []
    runtime_gaps: list[dict] = []

    for line_no, original in enumerate(csv_rows(text), 1):
        if not original or str(original[0] or "").strip().startswith("#"):
            continue

        robust, robust_status = robust_row(original)
        if robust is None:
            continue
        f = row_to_fields(robust)
        word = clean_text(f["VocabKanji"]).replace(" ", "")
        rd = reading_from_furigana(f["VocabFurigana"], word)
        level_match = LEVEL_RE.search(f"{f['Deck']} {f['Tags']}")
        level = f"N{level_match.group(1)}" if level_match else ""
        meaning = clean_text(f["VocabDefTC"])
        if word and rd:
            source_entries.append(Entry("core-source", level or "Unknown", word, rd, meaning, robust_status))

        rr, runtime_status = runtime_row(original)
        reason = []
        if rr is None:
            reason.append(runtime_status)
        else:
            rf = row_to_fields(rr)
            rw = clean_text(rf["VocabKanji"]).replace(" ", "")
            rrd = reading_from_furigana(rf["VocabFurigana"], rw)
            rmeaning = clean_text(rf["VocabDefTC"])
            lm = LEVEL_RE.search(f"{rf['Deck']} {rf['Tags']}")
            rlevel = f"N{lm.group(1)}" if lm else ""
            if not rw:
                reason.append("missing-word")
            if not rrd:
                reason.append("missing-reading")
            if not rmeaning:
                reason.append("missing-tc-meaning")
            if not rlevel:
                reason.append("missing-jlpt-level")
            if not reason:
                runtime_entries.append(Entry("runtime-core", rlevel, rw, rrd, rmeaning, runtime_status))

        if reason and word and rd:
            runtime_gaps.append({
                "line": line_no,
                "word": word,
                "reading": rd,
                "source_level": level,
                "reason": ";".join(reason),
                "source_row_width": len(original),
            })

    return dedupe_entries(source_entries), dedupe_entries(runtime_entries), runtime_gaps


def dedupe_entries(entries: Iterable[Entry]) -> list[Entry]:
    seen = set()
    out = []
    for entry in entries:
        marker = (entry.source, entry.level, entry.exact_key)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(entry)
    return out


def load_advanced_bundle(path: Path) -> list[Entry]:
    text = path.read_text(encoding="utf-8")
    start = text.find(",T=")
    end = text.find(";\nwindow.ADVANCED_WORDS", start)
    if start < 0 or end < 0:
        raise RuntimeError(f"cannot locate tuple payload in {path}")
    tuples = json.loads(text[start + 3:end])
    out = []
    for i, row in enumerate(tuples):
        if not isinstance(row, list) or len(row) < 4:
            continue
        level, reading, written, meaning = row[:4]
        word = str(written or reading or "").strip()
        rd = str(reading or "").strip()
        if word and rd:
            out.append(Entry("advanced-bundle", str(level), word, rd, str(meaning or ""), f"bundle-{i}"))
    return dedupe_entries(out)


def load_curated(path: Path) -> list[Entry]:
    text = path.read_text(encoding="utf-8")
    marker = "window.ADVANCED_WORDS = "
    start = text.find(marker)
    if start < 0:
        raise RuntimeError(f"cannot locate curated array in {path}")
    start = text.find("[", start + len(marker))
    end = text.find("].map", start)
    if start < 0 or end < 0:
        raise RuntimeError(f"cannot locate curated tuple payload in {path}")
    tuples = json.loads(text[start:end + 1])
    out = []
    for i, row in enumerate(tuples):
        if not isinstance(row, list) or len(row) < 4:
            continue
        level, display, reading, meaning = row[:4]
        word = str(display or reading or "").strip()
        rd = str(reading or "").strip()
        if not rd and is_kana(word):
            rd = word
        if word and rd:
            out.append(Entry("curated-supplement", str(level), word, rd, str(meaning or ""), f"curated-{i}"))
    return dedupe_entries(out)


def load_openjlpt(level: str, text: str) -> list[Entry]:
    data = json.loads(text)
    if isinstance(data, dict):
        rows = data.get("vocab") or data.get("words") or data.get("entries") or []
    else:
        rows = data
    out = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        word = str(item.get("word") or item.get("expression") or "").strip()
        rd = str(item.get("reading") or item.get("kana") or "").strip()
        meanings = item.get("meanings") or item.get("meaning") or []
        if isinstance(meanings, list):
            meaning = "; ".join(str(x) for x in meanings[:3])
        else:
            meaning = str(meanings or "")
        lv = str(item.get("level") or level).upper()
        if word and rd:
            out.append(Entry("openjlpt", lv if lv in LEVELS else level, word, rd, meaning))
    return dedupe_entries(out)


def load_waller(level: str, text: str) -> list[Entry]:
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for item in reader:
        word = str(item.get("kanji") or item.get("kana") or "").strip()
        rd = str(item.get("kana") or "").strip()
        meaning = str(item.get("waller_definition") or "").strip()
        if word and rd:
            out.append(Entry("waller", level, word, rd, meaning))
    return dedupe_entries(out)


def load_wordmaster(level: str, text: str) -> list[Entry]:
    data = json.loads(text)
    rows = data.get("words") if isinstance(data, dict) else data
    out = []
    for item in rows or []:
        if not isinstance(item, dict):
            continue
        word = str(item.get("word") or "").strip()
        rd = str(item.get("reading") or "").strip()
        lv = str(item.get("jlpt_level") or level).upper()
        meaning = str(item.get("translation_cn") or "").strip()
        if word and rd:
            out.append(Entry("wordmaster", lv if lv in LEVELS else level, word, rd, meaning))
    return dedupe_entries(out)


def load_references() -> tuple[list[Entry], dict[str, dict], dict[str, str]]:
    all_entries = []
    inventory: dict[str, dict] = {}
    errors: dict[str, str] = {}
    loaders = {"openjlpt": load_openjlpt, "waller": load_waller, "wordmaster": load_wordmaster}

    for source, by_level in REFERENCE_URLS.items():
        inventory[source] = {}
        for level, url in by_level.items():
            key = f"{source}:{level}"
            try:
                text = http_text(url)
                entries = loaders[source](level, text)
                inventory[source][level] = len(entries)
                all_entries.extend(entries)
            except Exception as exc:
                inventory[source][level] = 0
                errors[key] = str(exc)

    working_sources = {
        source for source in REFERENCE_URLS
        if sum(inventory[source].values()) >= 500
    }
    working_families = {SOURCE_FAMILY.get(source, source) for source in working_sources}
    if len(working_families) < 2:
        raise RuntimeError(
            f"need at least two working independent reference families; got {sorted(working_families)}; errors={errors}"
        )
    return dedupe_entries(all_entries), inventory, errors


def build_indexes(entries: Iterable[Entry]):
    by_exact: dict[str, list[Entry]] = defaultdict(list)
    by_variant: dict[str, list[Entry]] = defaultdict(list)
    by_skeleton: dict[str, list[Entry]] = defaultdict(list)
    by_reading: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        by_exact[entry.exact_key].append(entry)
        by_variant[entry.variant_key].append(entry)
        for rd in reading_aliases(entry.word, entry.reading):
            sk = loose_kanji_skeleton(entry.word)
            if sk:
                by_skeleton[f"{rd}|{sk}"].append(entry)
        by_reading[loose_kana(entry.reading)].append(entry)
    return {
        "exact": by_exact,
        "variant": by_variant,
        "skeleton": by_skeleton,
        "reading": by_reading,
    }


def match_entry(ref: Entry, indexes: dict[str, dict[str, list[Entry]]]) -> tuple[str, list[Entry]]:
    exact = indexes["exact"].get(ref.exact_key, [])
    if exact:
        return "exact", exact

    loose = indexes["variant"].get(ref.variant_key, [])
    if loose:
        return "kana/long-mark", loose

    sk = loose_kanji_skeleton(ref.word)
    if sk:
        for rd in reading_aliases(ref.word, ref.reading):
            matches = indexes["skeleton"].get(f"{rd}|{sk}", [])
            if matches:
                normal_ref = loose_kana(ref.reading)
                normal_cur = {loose_kana(x.reading) for x in matches}
                kind = "okurigana/orthography"
                if normal_ref not in normal_cur:
                    kind = "suru-reading-alias"
                return kind, matches

    # Weak but pedagogically useful fallback: a kanji spelling can be represented
    # by an all-kana dictionary headword with the same reading. Keep it out of
    # "missing" but label it clearly for manual review.
    rd = loose_kana(ref.reading)
    if rd:
        weak = [
            e for e in indexes["reading"].get(rd, [])
            if is_kana(e.word) and loose_word(e.word) == rd
        ]
        if weak:
            return "kana-spelling-weak", weak

    return "", []


def reference_groups(references: Iterable[Entry]) -> dict[str, list[Entry]]:
    # Exact written form + reading is the primary group. This avoids merging homophones.
    groups: dict[str, list[Entry]] = defaultdict(list)
    for entry in references:
        groups[entry.exact_key].append(entry)
    return groups


def mode_level(entries: Iterable[Entry]) -> tuple[str, dict[str, int], dict[str, str]]:
    """Return a family-weighted consensus so derivative mirrors do not double-vote."""
    by_family: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        if entry.level not in LEVELS:
            continue
        by_family[SOURCE_FAMILY.get(entry.source, entry.source)].append(entry.level)
    level_order = {level: i for i, level in enumerate(LEVELS)}
    family_votes: dict[str, str] = {}
    for family, levels in by_family.items():
        counts = Counter(levels)
        family_votes[family] = sorted(counts, key=lambda x: (-counts[x], level_order.get(x, 99)))[0]
    counts = Counter(family_votes.values())
    if not counts:
        return "", {}, family_votes
    winner = sorted(counts, key=lambda x: (-counts[x], level_order.get(x, 99)))[0]
    return winner, dict(counts), family_votes


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def audit(out_dir: Path) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    core_text, core_url = first_text(CORE_URLS)
    source_core, runtime_core, raw_runtime_gaps = parse_core(core_text)
    advanced = load_advanced_bundle(ROOT / "data" / "advanced_vocab.js")
    curated = load_curated(ROOT / "advanced_words_curated.js")
    runtime_all = dedupe_entries([*runtime_core, *curated, *advanced])

    refs, source_inventory, source_errors = load_references()

    runtime_idx = build_indexes(runtime_all)
    adv_idx = build_indexes([*curated, *advanced])
    source_core_idx = build_indexes(source_core)
    runtime_core_idx = build_indexes(runtime_core)
    runtime_exact = runtime_idx["exact"]

    missing_high: list[dict] = []
    missing_single: list[dict] = []
    level_conflicts: list[dict] = []
    variant_matches: list[dict] = []

    ref_groups = reference_groups(refs)
    for key, group in sorted(ref_groups.items(), key=lambda kv: kv[0]):
        sources = sorted({e.source for e in group})
        families = sorted({SOURCE_FAMILY.get(e.source, e.source) for e in group})
        consensus_level, level_votes, family_level_votes = mode_level(group)
        example = group[0]
        match_type, current_matches = match_entry(example, runtime_idx)

        common = {
            "word": example.word,
            "reading": example.reading,
            "consensus_level": consensus_level,
            "level_votes": json.dumps(level_votes, ensure_ascii=False, sort_keys=True),
            "family_level_votes": json.dumps(family_level_votes, ensure_ascii=False, sort_keys=True),
            "reference_sources": "|".join(sources),
            "reference_families": "|".join(families),
            "support_count": len(families),
        }

        if current_matches:
            current_levels = sorted({e.level for e in current_matches if e.level})
            current_sources = sorted({e.source for e in current_matches})
            if match_type != "exact":
                variant_matches.append({
                    **common,
                    "current_forms": "|".join(sorted({e.word for e in current_matches})),
                    "current_readings": "|".join(sorted({e.reading for e in current_matches})),
                    "current_levels": "|".join(current_levels),
                    "current_sources": "|".join(current_sources),
                    "match_type": match_type,
                })
            if consensus_level and current_levels and consensus_level not in current_levels:
                level_conflicts.append({
                    **common,
                    "current_levels": "|".join(current_levels),
                    "current_sources": "|".join(current_sources),
                    "match_type": match_type,
                })
            continue

        target = missing_high if len(families) >= 2 else missing_single
        target.append({
            **common,
            "candidate_type": candidate_type(example.word, example.reading),
            "example_meaning": next((e.meaning for e in group if e.meaning), ""),
        })

    # Runtime gaps that can become true final holes because the build considers them core
    # and therefore may exclude them from the advanced bundle.
    runtime_missing: list[dict] = []
    for gap in raw_runtime_gaps:
        key = exact_key(gap["word"], gap["reading"])
        if key not in source_core_idx["exact"]:
            continue
        if key in runtime_core_idx["exact"]:
            continue
        covered_by_supplement = key in adv_idx["exact"]
        runtime_missing.append({
            **gap,
            "covered_by_curated_or_advanced": "yes" if covered_by_supplement else "no",
            "final_runtime_hole": "no" if covered_by_supplement else "yes",
        })

    # Broad per-level coverage across the union of all external source entries.
    level_summary = {}
    for level in LEVELS:
        level_refs = [e for e in refs if e.level == level]
        unique_ref = {e.exact_key: e for e in level_refs}
        exact_count = 0
        variant_count = 0
        missing_count = 0
        for e in unique_ref.values():
            match_type, matches = match_entry(e, runtime_idx)
            if match_type == "exact":
                exact_count += 1
            elif matches:
                variant_count += 1
            else:
                missing_count += 1
        denominator = len(unique_ref)
        level_summary[level] = {
            "reference_unique": denominator,
            "exact_covered": exact_count,
            "variant_covered": variant_count,
            "missing": missing_count,
            "coverage_pct": round((exact_count + variant_count) * 100 / denominator, 2) if denominator else None,
        }

    # Consensus coverage is the more decision-useful metric: only groups supported
    # by both independent reference families are included.
    consensus_level_summary = {}
    for level in LEVELS:
        rows = []
        for group in ref_groups.values():
            families = {SOURCE_FAMILY.get(e.source, e.source) for e in group}
            if len(families) < 2:
                continue
            consensus_level, _, _ = mode_level(group)
            if consensus_level == level:
                rows.append(group[0])
        exact_count = 0
        variant_count = 0
        missing_count = 0
        for e in rows:
            match_type, matches = match_entry(e, runtime_idx)
            if match_type == "exact":
                exact_count += 1
            elif matches:
                variant_count += 1
            else:
                missing_count += 1
        denominator = len(rows)
        consensus_level_summary[level] = {
            "consensus_reference_unique": denominator,
            "exact_covered": exact_count,
            "variant_covered": variant_count,
            "missing": missing_count,
            "coverage_pct": round((exact_count + variant_count) * 100 / denominator, 2) if denominator else None,
        }

    final_holes = [x for x in runtime_missing if x["final_runtime_hole"] == "yes"]
    summary = {
        "generated_at_utc": generated_at,
        "core_source_url": core_url,
        "source_inventory": source_inventory,
        "source_errors": source_errors,
        "current": {
            "core_source_unique": len({e.exact_key for e in source_core}),
            "runtime_core_unique": len({e.exact_key for e in runtime_core}),
            "curated_unique": len({e.exact_key for e in curated}),
            "advanced_bundle_unique": len({e.exact_key for e in advanced}),
            "runtime_merged_unique": len({e.exact_key for e in runtime_all}),
        },
        "audit": {
            "high_confidence_missing": len(missing_high),
            "single_source_gaps": len(missing_single),
            "level_conflicts": len(level_conflicts),
            "variant_matches": len(variant_matches),
            "runtime_parser_gaps": len(runtime_missing),
            "runtime_final_holes": len(final_holes),
        },
        "level_summary": level_summary,
        "consensus_level_summary": consensus_level_summary,
        "method": {
            "high_confidence_missing": "Absent from current runtime set and present in >=2 independent reference families; OpenJLPT and Waller are intentionally counted as one derivative family.",
            "single_source_gap": "Absent from current runtime set but present in only one external reference family.",
            "level_conflict": "Word is present, but external consensus level is not among current site levels.",
            "runtime_final_hole": "Core source has word+reading; current runtime core parser rejects it; curated/advanced do not restore it.",
            "variant_match": "No exact key, but a conservative kana, okurigana/orthography, suru-reading, or kana-spelling relation matches.",
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "coverage_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    write_csv(out_dir / "missing_high_confidence.csv", missing_high,
              ["word","reading","consensus_level","level_votes","family_level_votes","reference_sources","reference_families","support_count","candidate_type","example_meaning"])
    write_csv(out_dir / "missing_single_source.csv", missing_single,
              ["word","reading","consensus_level","level_votes","family_level_votes","reference_sources","reference_families","support_count","candidate_type","example_meaning"])
    write_csv(out_dir / "level_conflicts.csv", level_conflicts,
              ["word","reading","consensus_level","level_votes","family_level_votes","reference_sources","reference_families","support_count","current_levels","current_sources","match_type"])
    write_csv(out_dir / "variant_matches.csv", variant_matches,
              ["word","reading","consensus_level","level_votes","family_level_votes","reference_sources","reference_families","support_count","current_forms","current_readings","current_levels","current_sources","match_type"])
    write_csv(out_dir / "runtime_missing.csv", runtime_missing,
              ["line","word","reading","source_level","reason","source_row_width","covered_by_curated_or_advanced","final_runtime_hole"])

    inventory_rows = []
    for source, levels in source_inventory.items():
        for level, count in levels.items():
            inventory_rows.append({
                "source": source,
                "family": SOURCE_FAMILY.get(source, source),
                "level": level,
                "count": count,
                "error": source_errors.get(f"{source}:{level}", ""),
            })
    write_csv(out_dir / "source_inventory.csv", inventory_rows, ["source","family","level","count","error"])

    readme = render_readme(summary, missing_high[:40], final_holes[:40])
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    return summary


def render_readme(summary: dict, missing_examples: list[dict], runtime_examples: list[dict]) -> str:
    lines = [
        "# JLPT Vocabulary Coverage Audit",
        "",
        f"Generated: `{summary['generated_at_utc']}`",
        "",
        "This is an **audit-only** report. It does not automatically add, delete, or re-level vocabulary.",
        "",
        "## Current runtime inventory",
        "",
        "| Layer | Unique entries |",
        "|---|---:|",
        f"| Core source (robust parse) | {summary['current']['core_source_unique']:,} |",
        f"| Core accepted by current browser parser | {summary['current']['runtime_core_unique']:,} |",
        f"| Curated supplement | {summary['current']['curated_unique']:,} |",
        f"| Advanced bundle | {summary['current']['advanced_bundle_unique']:,} |",
        f"| Final merged runtime set | {summary['current']['runtime_merged_unique']:,} |",
        "",
        "## External reference inventory",
        "",
        "| Source | N5 | N4 | N3 | N2 | N1 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for source, counts in summary["source_inventory"].items():
        lines.append("| " + source + " | " + " | ".join(f"{counts.get(level, 0):,}" for level in LEVELS) + " |")

    lines += [
        "",
        "## Coverage by level",
        "",
        "| Level | Reference entries | Exact | Variant | Missing | Coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for level in LEVELS:
        row = summary["level_summary"][level]
        lines.append(
            f"| {level} | {row['reference_unique']:,} | {row['exact_covered']:,} | "
            f"{row['variant_covered']:,} | {row['missing']:,} | {row['coverage_pct']}% |"
        )

    lines += [
        "",
        "## Consensus coverage (recommended metric)",
        "",
        "| Level | Consensus entries | Exact | Variant/related | Missing | Coverage |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for level in LEVELS:
        row = summary["consensus_level_summary"][level]
        lines.append(
            f"| {level} | {row['consensus_reference_unique']:,} | {row['exact_covered']:,} | "
            f"{row['variant_covered']:,} | {row['missing']:,} | {row['coverage_pct']}% |"
        )

    a = summary["audit"]
    lines += [
        "",
        "## Findings",
        "",
        f"- High-confidence missing (supported by >=2 independent external families): **{a['high_confidence_missing']:,}**",
        f"- Single-source gaps requiring review: **{a['single_source_gaps']:,}**",
        f"- Level conflicts: **{a['level_conflicts']:,}**",
        f"- Conservative variant matches: **{a['variant_matches']:,}**",
        f"- Core rows rejected by current runtime parser: **{a['runtime_parser_gaps']:,}**",
        f"- Core rows rejected and not restored by supplements: **{a['runtime_final_holes']:,}**",
        "",
        "### Sample high-confidence missing entries",
        "",
        "| Word | Reading | Consensus | Sources |",
        "|---|---|---|---|",
    ]
    for row in missing_examples:
        lines.append(f"| {row['word']} | {row['reading']} | {row['consensus_level']} | {row['reference_families']} ({row['reference_sources']}) |")
    if not missing_examples:
        lines.append("| — | — | — | — |")

    lines += [
        "",
        "### Sample runtime final holes",
        "",
        "| Word | Reading | Source level | Reason |",
        "|---|---|---|---|",
    ]
    for row in runtime_examples:
        lines.append(f"| {row['word']} | {row['reading']} | {row['source_level']} | {row['reason']} |")
    if not runtime_examples:
        lines.append("| — | — | — | — |")

    lines += [
        "",
        "## Interpretation",
        "",
        "- JLPT does not publish a fixed official vocabulary list for the current test, so level disagreements are expected.",
        "- `missing_high_confidence.csv` is the best candidate list for manual addition review.",
        "- `runtime_missing.csv` is the first place to inspect for actual application bugs.",
        "- `level_conflicts.csv` should be reviewed rather than auto-applied, because external sources frequently disagree.",
        "- `missing_single_source.csv` is intentionally lower confidence and should not be bulk-imported.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="audit/vocab/results", help="output directory relative to repo root")
    args = parser.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    try:
        summary = audit(out)
    except Exception as exc:
        print(f"AUDIT FAILED: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nReports written to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
