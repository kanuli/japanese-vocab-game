#!/usr/bin/env python3
"""Conservatively refine every core vocabulary fallback after the exact JMdict build.

This pass does not scrape proprietary dictionaries. It uses the project's reusable
Tomoshi/JMdict zh-TW data to compare every ambiguous exact-form+reading candidate
against the core deck's existing Traditional-Chinese meaning. A candidate is accepted
only when semantic evidence is strong and clearly separated from the alternatives.
The small external-dictionary cross-check overlay is treated as manually validated
metadata and folded into the generated core overlay/audit so runtime and audit agree.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from collections import defaultdict
from pathlib import Path

from opencc import OpenCC

import build_vocab_bundle as base
import build_vocab_bundle_exact as exact

ROOT = base.ROOT
DB_PATH = Path(os.environ.get("TOMOSHI_DB", "/tmp/tomoshi.db"))
AUDIT_PATH = ROOT / "data" / "vocab_audit.json"
EXTERNAL_PATH = ROOT / "data" / "vocab_external_crosscheck.js"
CC = OpenCC("s2t")

# Conservative traditional/old-glyph -> Japanese standard glyph normalization.
# Used ONLY for dictionary form lookup, never to rewrite the user's runtime display.
JP_GLYPH_MAP = str.maketrans({
    "嚙":"噛", "搔":"掻", "剝":"剥", "頰":"頬", "歲":"歳", "黑":"黒",
    "戶":"戸", "惠":"恵", "德":"徳", "瀨":"瀬", "濱":"浜", "邊":"辺",
    "邉":"辺", "澤":"沢", "廣":"広", "國":"国", "學":"学", "會":"会",
    "氣":"気", "體":"体", "臺":"台", "萬":"万", "圓":"円", "鐵":"鉄",
    "驛":"駅", "號":"号", "壓":"圧", "處":"処", "醫":"医", "藥":"薬",
    "舊":"旧", "樂":"楽", "櫻":"桜", "觀":"観", "實":"実", "讀":"読",
    "圖":"図", "聲":"声", "假":"仮", "變":"変", "續":"続", "關":"関",
    "應":"応", "寫":"写", "畫":"画", "轉":"転", "點":"点", "鹽":"塩",
})

STOP_CHARS = set("的了是在有和與或為於及之等個一種表示用作作為者也又而可會")
PUNCT_RE = re.compile(r"[\s\u3000，,。；;、：:！？!?／/\\|（）()［］\[\]【】{}<>《》〈〉「」『』…·・~～—–_-]+")
FURI_RE = re.compile(r"([\u3400-\u9fff々〆ヵヶ]+)\[([ぁ-ゖァ-ヺー]+)\]")
KANA_BRACKET_RE = re.compile(r"\[([ぁ-ゖァ-ヺー]+)\]")


def load_manual_crosschecks() -> dict[str, dict]:
    if not EXTERNAL_PATH.exists():
        return {}
    text = EXTERNAL_PATH.read_text(encoding="utf-8")
    m = re.search(r"const\s+rows\s*=\s*(\[.*?\])\s*;", text, re.S)
    if not m:
        return {}
    try:
        rows = json.loads(m.group(1))
    except Exception:
        return {}
    out = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 4:
            continue
        reading, display, level, meaning = map(str, row[:4])
        if reading and display and level in exact.VALID_LEVELS and meaning:
            out[f"{reading}|{display}"] = {"level": level, "meaning": meaning}
    return out


def kana_key(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "").strip())
    out = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def surface_form(value: str) -> str:
    """Normalize safe orthographic notation for lookup, not for runtime display."""
    text = base.clean_text(value or "").replace(" ", "")
    text = FURI_RE.sub(r"\1", text)
    text = KANA_BRACKET_RE.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    return text.translate(JP_GLYPH_MAP)


def build_normalized_form_index(conn: sqlite3.Connection, core_records: list[dict], entry_info: dict) -> dict[str, list[dict]]:
    wanted = defaultdict(list)
    for rec in core_records:
        surf = surface_form(rec["display"])
        if surf:
            wanted[surf].append(rec)

    normalized_entry = {}
    for eid, info in entry_info.items():
        normalized_entry[eid] = {
            "readings": {kana_key(x) for x in (info.get("readings") or set())},
            "written": {surface_form(x) for x in (info.get("written") or set())},
            "common": bool(info.get("common")),
        }

    result = defaultdict(list)
    for row in conn.execute("SELECT text, entry_id, is_kana, is_common FROM forms"):
        form = surface_form(str(row[0] or ""))
        if not form or form not in wanted:
            continue
        eid = str(row[1])
        info = normalized_entry.get(eid) or {}
        readings = info.get("readings") or set()
        for rec in wanted[form]:
            if kana_key(rec["reading"]) not in readings:
                continue
            result[rec["key"]].append({
                "entry_id": eid,
                "form_common": bool(row[3]),
                "entry_common": bool(info.get("common")),
                "written_exact": form in (info.get("written") or set()),
                "normalized_match": True,
            })
    return result


def norm_text(value: str) -> str:
    text = CC.convert(base.clean_text(value or "")).lower()
    text = text.replace("裏", "裡").replace("甚麼", "什麼")
    text = PUNCT_RE.sub(";", text).strip(";")
    return text


def plain(value: str) -> str:
    return re.sub(r"[^\u3400-\u9fffA-Za-z0-9ぁ-ゖァ-ヺー]", "", norm_text(value))


def fragments(value: str) -> list[str]:
    return [x for x in norm_text(value).split(";") if x]


def dice(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def ngrams(text: str, n: int) -> set[str]:
    if len(text) < n:
        return {text} if text else set()
    return {text[i:i+n] for i in range(len(text) - n + 1)}


def semantic_similarity(a: str, b: str) -> float:
    aa, bb = plain(a), plain(b)
    if not aa or not bb:
        return 0.0
    if aa == bb:
        return 1.0

    containment = 0.0
    for x in fragments(a):
        xp = plain(x)
        if not xp:
            continue
        for y in fragments(b):
            yp = plain(y)
            if not yp:
                continue
            if xp == yp:
                containment = max(containment, 0.98 if len(xp) >= 2 else 0.84)
            elif min(len(xp), len(yp)) >= 2 and (xp in yp or yp in xp):
                ratio = min(len(xp), len(yp)) / max(len(xp), len(yp))
                containment = max(containment, 0.70 + 0.20 * ratio)

    bigram = dice(ngrams(aa, 2), ngrams(bb, 2))
    achar = {c for c in aa if c not in STOP_CHARS}
    bchar = {c for c in bb if c not in STOP_CHARS}
    chars = dice(achar, bchar)
    structural = 0.68 * bigram + 0.32 * chars
    return min(1.0, max(containment, structural))


def candidate_level(eid: str, original_level: str, waller_by_id: dict,
                    entry_info: dict, tomoshi_jlpt: dict) -> tuple[str, str]:
    return exact.level_for(
        eid,
        waller_by_id.get(eid, ""),
        original_level,
        999999,
        entry_info,
        tomoshi_jlpt,
    )


def semantic_resolve(rec: dict, options: list[dict], zh: dict, waller_by_id: dict,
                     entry_info: dict, tomoshi_jlpt: dict, anchor: str) -> tuple[str | None, list[dict]]:
    unique = {x["entry_id"]: x for x in options}
    scored = []
    for eid, opt in unique.items():
        meaning = zh.get(eid, "")
        if not meaning:
            continue
        sem = semantic_similarity(anchor, meaning)
        lvl, _src = candidate_level(eid, rec["level"], waller_by_id, entry_info, tomoshi_jlpt)
        level_match = lvl == rec["level"]
        meta = (
            (0.035 if opt.get("form_common") else 0.0)
            + (0.025 if opt.get("entry_common") else 0.0)
            + (0.020 if opt.get("written_exact") else 0.0)
            + (0.035 if level_match else 0.0)
        )
        scored.append({
            "entryId": eid,
            "meaning": meaning,
            "semantic": round(sem, 4),
            "score": round(sem + meta, 4),
            "candidateLevel": lvl,
            "levelMatch": level_match,
            "formCommon": bool(opt.get("form_common")),
            "entryCommon": bool(opt.get("entry_common")),
        })
    scored.sort(key=lambda x: (x["score"], x["semantic"], x["entryCommon"], x["formCommon"]), reverse=True)
    if not scored:
        return None, scored
    if len(scored) == 1:
        return (scored[0]["entryId"] if scored[0]["semantic"] >= 0.58 else None), scored

    best, second = scored[0], scored[1]
    sem_margin = best["semantic"] - second["semantic"]
    score_margin = best["score"] - second["score"]
    accept = (
        (best["semantic"] >= 0.82 and score_margin >= 0.06)
        or (best["semantic"] >= 0.68 and sem_margin >= 0.12 and score_margin >= 0.09)
        or (best["semantic"] >= 0.58 and sem_margin >= 0.22 and score_margin >= 0.16 and best["levelMatch"])
    )
    return (best["entryId"] if accept else None), scored


def main() -> int:
    if not DB_PATH.exists():
        raise RuntimeError(f"Tomoshi SQLite database not found: {DB_PATH}")
    if not AUDIT_PATH.exists():
        raise RuntimeError("Run build_vocab_bundle_exact.py before ambiguity refinement")

    manual = load_manual_crosschecks()
    conn = sqlite3.connect(str(DB_PATH))
    zh, entry_info, tomoshi_jlpt, _zh_total = exact.load_tomoshi(conn)
    core_text = base.fetch_text(base.URLS["core"])
    core_records = exact.parse_core_records(core_text)
    exact_form_index = exact.build_core_form_index(conn, core_records, entry_info)
    normalized_form_index = build_normalized_form_index(conn, core_records, entry_info)

    words_data = base.fetch_json(base.URLS["words"])
    waller_by_id = {}
    for raw in words_data.get("words") or []:
        eid = str(raw.get("id") or "").strip()
        if eid:
            waller_by_id[eid] = exact.normalized_level(raw.get("jlpt_waller"))

    overlay = []
    rows_for_semantic_audit = []
    residual = []
    semantic_selected = []
    stats = {
        "total": len(core_records),
        "exactEntryResolved": 0,
        "ambiguousPairs": 0,
        "unresolvedPairs": 0,
        "tomoshiMeaningsApplied": 0,
        "originalMeaningFallback": 0,
        "meaningChanged": 0,
        "levelChanged": 0,
        "semanticResolvedPairs": 0,
        "manualSecondaryCrosscheckApplied": 0,
        "semanticCandidatesReviewed": 0,
        "normalizedFormReadingRecoveredPairs": 0,
    }

    for rec in core_records:
        key = rec["key"]
        raw_options = exact_form_index.get(key, [])
        normalized_options = normalized_form_index.get(key, [])
        options = raw_options or normalized_options
        if not raw_options and normalized_options:
            stats["normalizedFormReadingRecoveredPairs"] += 1

        eid, was_ambiguous = exact.choose_core_entry(options, zh)
        if was_ambiguous:
            stats["ambiguousPairs"] += 1

        manual_item = manual.get(key)
        scored = []
        selected_semantically = False
        if eid is None and options:
            anchor = manual_item["meaning"] if manual_item else rec["meaning"]
            selected, scored = semantic_resolve(
                rec, options, zh, waller_by_id, entry_info, tomoshi_jlpt, anchor
            )
            stats["semanticCandidatesReviewed"] += 1
            if selected:
                eid = selected
                selected_semantically = True
                stats["semanticResolvedPairs"] += 1
                semantic_selected.append({
                    "key": key,
                    "lookupDisplay": surface_form(rec["display"]),
                    "originalMeaning": rec["meaning"],
                    "anchorMeaning": anchor,
                    "selectedEntryId": eid,
                    "candidates": scored,
                })

        if eid is None:
            stats["unresolvedPairs"] += 1
        else:
            stats["exactEntryResolved"] += 1

        meaning = rec["meaning"]
        meaning_source = "core-original-fallback"
        level = rec["level"]
        level_source = "core-deck"

        if eid and eid in zh:
            meaning = zh[eid]
            meaning_source = "tomoshi-entry-id-semantic-resolve" if selected_semantically else ("tomoshi-entry-id-normalized-form" if not raw_options and normalized_options else "tomoshi-entry-id")
            stats["tomoshiMeaningsApplied"] += 1
            level, level_source = candidate_level(
                eid, rec["level"], waller_by_id, entry_info, tomoshi_jlpt
            )

        if manual_item:
            meaning = manual_item["meaning"]
            level = manual_item["level"]
            meaning_source = "manual-secondary-crosscheck"
            level_source = "manual-secondary-crosscheck"
            stats["manualSecondaryCrosscheckApplied"] += 1

        if meaning_source == "core-original-fallback":
            stats["originalMeaningFallback"] += 1
            residual.append({
                "key": key,
                "lookupDisplay": surface_form(rec["display"]),
                "lookupReading": kana_key(rec["reading"]),
                "originalMeaning": rec["meaning"],
                "level": rec["level"],
                "candidateCount": len({x["entry_id"] for x in options}),
                "candidates": scored[:12],
            })

        if meaning != rec["meaning"]:
            stats["meaningChanged"] += 1
        if level != rec["level"]:
            stats["levelChanged"] += 1

        overlay.append([rec["reading"], rec["display"], level, meaning, meaning_source, level_source, eid])
        rows_for_semantic_audit.append({
            "reading": rec["reading"], "display": rec["display"],
            "meaning": meaning, "level": level, "source": "core-refined"
        })

    refinement_fatal = []
    exact.semantic_audit(rows_for_semantic_audit, refinement_fatal)
    for row in rows_for_semantic_audit:
        if row["display"] == "西瓜" and row["reading"] == "すいか":
            if "西瓜" not in row["meaning"] or "天邊一朵雲" in row["meaning"]:
                refinement_fatal.append({"type": "suika_semantic_sentinel_failed", "meaning": row["meaning"]})
    if refinement_fatal:
        raise RuntimeError(f"refinement semantic audit failed: {refinement_fatal[:5]}")

    exact.write_core_overlay(overlay, {
        "version": "core-verified-20260826-v3-normalized-refined",
        "generated": exact.datetime.now(exact.timezone.utc).isoformat(),
        "rows": len(overlay),
        "meaningPolicy": "Tomoshi zh-TW by exact JMdict entry ID; safe form notation/kana-script normalization is used only when raw exact lookup has no candidate; all ambiguous candidates reviewed by conservative Traditional-Chinese semantic scoring; manual secondary cross-checks folded in; unresolved values retained",
        "levelPolicy": "JLPT Waller/Tomoshi JLPT > embedded entry level > original core deck; validated external cross-check level may override exact key",
        "semanticResolver": "strong semantic similarity + separation margin; commonness/JLPT agreement only small tie-breakers",
    })

    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    audit["coreAudit"] = stats
    audit["coreUnresolvedSamples"] = [x["key"] for x in residual[:100]]
    audit["coreUnresolvedAll"] = residual
    audit["coreSemanticResolved"] = semantic_selected
    audit.setdefault("counts", {})["coreMeaningFallbackAfterRefinement"] = len(residual)
    audit["counts"]["coreSecondaryCrosschecksApplied"] = stats["manualSecondaryCrosscheckApplied"]
    audit["counts"]["coreSemanticResolvedPairs"] = stats["semanticResolvedPairs"]
    audit["counts"]["coreNormalizedFormReadingRecoveredPairs"] = stats["normalizedFormReadingRecoveredPairs"]
    audit.setdefault("policy", {})["coreRefinement"] = (
        "Every original core fallback is reviewed against all safe exact-equivalent form+reading Tomoshi/JMdict candidates. "
        "Bracketed furigana notation, Unicode/Japanese glyph normalization and hiragana/katakana reading equivalence are allowed only when the raw exact lookup has no candidate. "
        "Automatic semantic selection still requires strong Traditional-Chinese agreement and a clear margin. "
        "Mazii/MOJi/時雨 are secondary manual validation only; their proprietary dictionary text is not bulk-copied."
    )
    audit["refinementFatalIssueCount"] = 0
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"semantic_resolved={len(semantic_selected)} residual_fallback={len(residual)} manual_crosschecks={len(manual)}")
    if residual:
        print("residual samples:")
        for item in residual[:60]:
            print(" ", item["key"], "lookup=", item["lookupDisplay"], "/", item["lookupReading"], "=>", item["originalMeaning"], "candidates=", item["candidateCount"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
