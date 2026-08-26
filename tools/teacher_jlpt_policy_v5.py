#!/usr/bin/env python3
"""JLPT teacher policy v5: independent-source lineage + targeted teacher anchors.

OpenJLPT and Japanese Language Data's Waller/Tanos classifications share the same
underlying Waller/Tanos lineage, so they must never be counted as two independent
votes.  This policy is layered on top of recalibrate_jlpt_teacher_v4 so the existing
exact-key audit, model allocation, provenance and output format remain reusable.

Teacher goal: classify a word at the earliest defensible study level, while keeping
unresolved source disagreements visible as grade C rather than hiding them.
"""
from __future__ import annotations

from collections import Counter

import recalibrate_jlpt_teacher_v4 as v4

VERSION = "20260826-teacher-v5-source-lineage"
RUNTIME_VERSION = "20260826-teacher-runtime-v2-lineage"
SOURCE_INDEPENDENCE = (
    "OpenJLPT and Japanese Language Data Waller/Tanos share one Waller/Tanos lineage; "
    "they are never counted as independent votes. Existing Tomoshi JLPT labels are "
    "also treated as legacy-lineage context unless independently validated."
)

# Exact keys independently checked against 時雨's learning dictionary/course labels
# or retained high-confidence teacher sentinels.  The level is a pedagogical study
# classification, not an official JLPT designation.
TEACHER_ANCHORS_V5 = {
    # Existing regression sentinels / previously checked exact keys.
    "まい|まい": "N2", "まい|舞": "N2", "まい|枚": "N5", "まい|毎": "N5",
    "すいか|西瓜": "N5", "これ|これ": "N5", "それ|それ": "N5",
    "おもしろい|面白い": "N5", "あかるい|明るい": "N5", "おわる|終わる": "N5",
    "べんきょう|勉強": "N5", "さんぽ|散歩": "N5", "だんだん|だんだん": "N5",
    "もし|もし": "N4", "ふん|分": "N5", "キロ|キロ": "N5",
    "せっけん|石鹸": "N5", "せっけん|石鹸[けん]": "N5",
    "さらいげつ|再来月": "N5", "さらいねん|再来年": "N5",
    "まんなか|真ん中": "N4", "つくる|造る": "N5",
    "キログラム|キログラム": "N5", "キロメートル|キロメートル": "N5",
    "スプーン|スプーン": "N5", "フォーク|フォーク": "N5", "ポケット|ポケット": "N5",
    "せんせんしゅう|先々週": "N3", "じどうしゃ|自動車": "N3",
    "じょうぶ|丈夫": "N5", "りゅうがく|留学": "N5",
    # High-risk N1/N2 conflict queue independently checked against 時雨.
    "あと|跡": "N3", "いじめる|いじめる": "N4", "いたずら|いたずら": "N3",
    "いっか|一家": "N3", "えんじょ|援助": "N2", "えんぜつ|演説": "N2",
    "おおいに|大いに": "N3", "およぼす|及ぼす": "N2", "かいごう|会合": "N2",
    "かがく|化学": "N3", "かたい|堅い": "N4", "かみ|上": "N5", "から|空": "N5",
    "がいこう|外交": "N2", "がく|額": "N2", "きし|岸": "N2", "きり|霧": "N3",
    "きんこ|金庫": "N2", "きんせん|金銭": "N2", "きんゆう|金融": "N2",
    "ぎん|銀": "N5", "くみあい|組合": "N3", "くれる|暮れる": "N4",
    "げしゅく|下宿": "N2", "こうさい|交際": "N2", "こらえる|堪える": "N2",
    "ころす|殺す": "N3", "さいばん|裁判": "N2", "さけぶ|叫ぶ": "N3",
    "さべつ|差別": "N3", "したぎ|下着": "N5", "しつぎょう|失業": "N3",
    "しばい|芝居": "N2", "しも|霜": "N2", "しゅうきょう|宗教": "N3",
    "しょうにん|商人": "N3", "しょくりょう|食糧": "N3", "しょさい|書斎": "N2",
    "しょめい|署名": "N2", "しり|尻": "N3", "じょゆう|女優": "N3",
    "すっと|すっと": "N3", "すみ|隅": "N4", "せいねん|青年": "N3",
    "それとも|其れとも": "N3", "たいき|大気": "N2", "たいはん|大半": "N3",
    "たいほ|逮捕": "N2", "ちく|地区": "N3", "ちじ|知事": "N1",
    "ちょうだい|頂戴": "N3", "ちり|地理": "N4", "つうじる|通じる": "N3",
    "つかまる|捕まる": "N3", "つみ|罪": "N3", "てきよう|適用": "N2",
    "てんねん|天然": "N2", "どれ|何れ": "N3", "のうみん|農民": "N3",
    "のぼる|昇る": "N3", "はかせ|博士": "N2", "ひげき|悲劇": "N2",
    "ふこう|不幸": "N3", "ふじん|婦人": "N2", "レコード|レコード": "N3",
    # High-risk N2 queue independently checked in the same pass.
    "いのる|祈る": "N4", "かれら|彼ら": "N4", "きしゃ|汽車": "N4",
    "きぬ|絹": "N4", "けいかん|警官": "N5", "こうちょう|校長": "N5",
    "こぼれる|零れる": "N3", "じしん|地震": "N4", "じてん|辞典": "N4",
    "じゅうたん|絨毯": "N3", "たて|縦": "N5", "つける|漬ける": "N4",
    "つる|釣る": "N4", "どろぼう|泥棒": "N4", "れいぼう|冷房": "N3",
    "アクセサリー|アクセサリー": "N4", "ソフト|ソフト": "N4",
}


def _easier(*levels: str) -> str:
    vals = [x for x in levels if x in v4.VALID]
    return min(vals, key=lambda x: v4.IDX[x]) if vals else ""


def _lineage(op: str, wa: str) -> tuple[str, bool]:
    """Return one Waller-lineage level when internally consistent, plus conflict."""
    vals = [x for x in (op, wa) if x in v4.VALID]
    if not vals:
        return "", False
    if len(set(vals)) == 1:
        return vals[0], False
    return "", True


def choose_direct(row: dict, ev: dict[str, str]) -> tuple[str, str, str, bool]:
    """Source-lineage-aware replacement for v4.choose_direct."""
    key = row["key"]
    if key in TEACHER_ANCHORS_V5:
        return TEACHER_ANCHORS_V5[key], "A", "independent-teacher-anchor", False
    if ev.get("manual-secondary-exact"):
        return ev["manual-secondary-exact"], "A", "manual-secondary-exact", False

    core = ev.get("core-deck-exact", "")
    op = ev.get("openjlpt-exact", "")
    wa = ev.get("waller-exact", "")
    cur = ev.get("existing-direct", "")
    lineage, lineage_conflict = _lineage(op, wa)

    # Core deck and Waller/Tanos are different lineages. OpenJLPT and Waller are not.
    if core:
        if lineage:
            if core == lineage:
                return core, "A", "core+waller-lineage-corroborated", False
            span = abs(v4.IDX[core] - v4.IDX[lineage])
            if row.get("common"):
                return _easier(core, lineage), "C", "common-core-vs-waller-lineage-easier", True
            if span <= 1:
                return core, "C", "core-vs-waller-lineage-adjacent", True
            return core, "C", "core-vs-waller-lineage-large", True
        if lineage_conflict:
            vals = [x for x in (op, wa) if x in v4.VALID]
            if row.get("common"):
                return _easier(core, *vals), "C", "common-core-vs-internal-lineage-conflict-easier", True
            return core, "C", "core-vs-internal-lineage-conflict", True
        return core, "B", "core-exact", bool(cur and cur != core)

    # Non-core: an OpenJLPT+Waller agreement is still one lineage, therefore grade B.
    if lineage:
        conflict = bool(cur and cur != lineage)
        return lineage, "B" if not conflict else "C", (
            "waller-lineage-exact" if not conflict else "waller-lineage-vs-existing-conflict"
        ), conflict
    if lineage_conflict:
        vals = [x for x in (op, wa) if x in v4.VALID]
        if row.get("common"):
            return _easier(*vals), "C", "internal-waller-lineage-conflict-common-easier", True
        if cur in vals:
            return cur, "C", "internal-waller-lineage-conflict-existing-tiebreak", True
        centre = sum(v4.IDX[x] for x in vals) / len(vals)
        chosen = min(vals, key=lambda x: (abs(v4.IDX[x] - centre), v4.IDX[x]))
        return chosen, "C", "internal-waller-lineage-conflict-midpoint", True

    # Mechanical normalization only; collapse OpenJLPT/Waller to one lineage here too.
    norm_core = ev.get("core-deck-normalized", "")
    norm_op = ev.get("openjlpt-normalized", "")
    norm_wa = ev.get("waller-normalized", "")
    norm_lineage, norm_conflict = _lineage(norm_op, norm_wa)
    if norm_core and norm_lineage:
        if norm_core == norm_lineage:
            return norm_core, "B", "mechanically-normalized-core+waller-lineage", False
        return _easier(norm_core, norm_lineage) if row.get("common") else norm_core, "C", "mechanically-normalized-lineage-conflict", True
    if norm_core:
        return norm_core, "B", "mechanically-normalized-core", norm_conflict
    if norm_lineage:
        return norm_lineage, "B", "mechanically-normalized-waller-lineage", norm_conflict

    if cur:
        return cur, "B", "existing-direct-exact-row", False
    return "", "D", "estimate-required", False


def choose_runtime_direct(row: dict, ev: dict[str, str]) -> tuple[str, str, str, bool]:
    """Lineage-aware chooser for additive runtime supplement rows."""
    key = row["key"]
    if key in TEACHER_ANCHORS_V5:
        return TEACHER_ANCHORS_V5[key], "A", "independent-teacher-anchor", False
    if ev.get("manual") in v4.VALID:
        return ev["manual"], "A", "manual-secondary-exact", False

    core = ev.get("core", "") if ev.get("core") in v4.VALID else ""
    # OpenJLPT, Waller and Tomoshi's imported JLPT label are treated as one legacy
    # lineage unless a future provenance field proves an independent origin.
    legacy_vals = [ev.get(k, "") for k in ("openjlpt", "waller", "tomoshi")]
    legacy_vals = [x for x in legacy_vals if x in v4.VALID]
    unique = set(legacy_vals)
    legacy = next(iter(unique)) if len(unique) == 1 else ""
    legacy_conflict = len(unique) > 1

    if core and legacy:
        if core == legacy:
            return core, "A", "core+legacy-lineage-corroborated", False
        if row.get("common"):
            return _easier(core, legacy), "C", "runtime-common-core-vs-legacy-easier", True
        return core, "C", "runtime-core-vs-legacy-conflict", True
    if core and legacy_conflict:
        if row.get("common"):
            return _easier(core, *legacy_vals), "C", "runtime-common-core-vs-internal-legacy-easier", True
        return core, "C", "runtime-core-vs-internal-legacy-conflict", True
    if core:
        return core, "B", "runtime-core-exact", False
    if legacy:
        return legacy, "B", "runtime-legacy-lineage-exact", False
    if legacy_conflict:
        chosen = _easier(*legacy_vals) if row.get("common") else Counter(legacy_vals).most_common(1)[0][0]
        return chosen, "C", "runtime-internal-legacy-lineage-conflict", True
    return "", "D", "runtime-estimate-required", False


def install() -> None:
    """Patch v4 in-memory before v4.main() executes."""
    v4.TEACHER_ANCHORS.clear()
    v4.TEACHER_ANCHORS.update(TEACHER_ANCHORS_V5)
    v4.choose_direct = choose_direct

    original_core = v4.write_core
    original_adv = v4.write_advanced

    def write_core_v5(meta: dict, rows: list[dict]):
        meta = dict(meta)
        meta["teacherPolicyRevision"] = VERSION
        meta["sourceIndependence"] = SOURCE_INDEPENDENCE
        return original_core(meta, rows)

    def write_advanced_v5(meta: dict, rows: list[dict], recal: dict):
        recal["version"] = VERSION
        recal["policyRevision"] = "v5-source-lineage"
        recal["sourceIndependence"] = SOURCE_INDEPENDENCE
        recal["policy"] = (
            "Teacher audit per exact reading+display key. Independent teacher/manual anchors first; "
            "core deck and Waller/Tanos lineage are compared without double-counting OpenJLPT; "
            "unresolved disagreements remain grade C; only residual words are estimated; estimated "
            "N1 requires positive rarity evidence."
        )
        recal["sources"] = [
            "original 5mdld N1-N5 core deck",
            "Waller/Tanos lineage (Japanese Language Data + OpenJLPT; counted once)",
            "Mazii/MOJi/時雨 targeted exact secondary cross-check layer",
            "Tomoshi/JMdict commonness and frequency for residual estimation only",
        ]
        recal["independentTeacherAnchors"] = len(TEACHER_ANCHORS_V5)
        meta = dict(meta)
        meta["teacherPolicyRevision"] = VERSION
        meta["sourceIndependence"] = SOURCE_INDEPENDENCE
        return original_adv(meta, rows, recal)

    v4.write_core = write_core_v5
    v4.write_advanced = write_advanced_v5
