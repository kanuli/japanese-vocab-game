#!/usr/bin/env python3
"""Extend the teacher JLPT audit to every additive runtime vocabulary source.

The generated core+advanced bundle is audited by recalibrate_jlpt_teacher_v4.py.
Historically, however, advanced_words.js also loaded curated/manual supplement files
before/after that bundle.  Those rows could therefore bypass the generated audit and
reintroduce old estimated N1 labels at browser runtime.

This script parses every additive supplement currently loaded by advanced_words.js,
checks its intended exact (reading, display) key against the same reusable world JLPT
evidence, appends genuinely new keys to the teacher audit, and emits a small runtime
overlay.  The overlay is loaded after all supplement files so their displayed level
can never override the teacher-audited decision.

No proprietary dictionary is scraped here. Mazii/MOJi/時雨 remain represented only by
the repository's targeted exact manual cross-check layer.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import build_vocab_bundle_exact as exact
import recalibrate_jlpt_world as v1
import recalibrate_jlpt_teacher_v4 as v4

ROOT = Path(__file__).resolve().parents[1]
AUDIT_JSON = ROOT / "data" / "vocab_audit.json"
TEACHER_TSV = ROOT / "data" / "jlpt_teacher_audit.tsv"
OVERLAY_JS = ROOT / "data" / "vocab_teacher_runtime_overlay.js"
CURATED_JS = ROOT / "advanced_words_curated.js"
SUPPLEMENT_R_FILES = [
    ROOT / "data" / "coverage_deferred_manual.js",
    ROOT / "data" / "coverage_sourcecheck_manual.js",
    ROOT / "data" / "coverage_postreview_manual.js",
]
COMMON_FIXUPS = ROOT / "data" / "vocab_common_fixups.js"
VALID = set(v1.LEVELS)
IDX = {x: i for i, x in enumerate(v1.LEVELS)}


def key(reading: str, display: str) -> str:
    return f"{v1.norm(reading)}|{v1.norm(display)}"


def parse_curated() -> list[dict]:
    text = CURATED_JS.read_text(encoding="utf-8")
    m = re.search(r"window\.ADVANCED_WORDS\s*=\s*(\[.*?\])\.map", text, re.S)
    if not m:
        raise RuntimeError("cannot parse advanced_words_curated.js")
    rows = json.loads(m.group(1))
    out = []
    for x in rows:
        if not isinstance(x, list) or len(x) < 4:
            continue
        level, written, kana, meaning = (str(x[i] or "") for i in range(4))
        # Curated tuples are intended as [level, written/display, reading, meaning].
        # Kana-only/katakana entries leave reading blank because display=reading.
        reading = kana or written
        display = written or reading
        if reading and display and meaning and level in VALID:
            out.append({"reading": reading, "display": display, "meaning": meaning,
                        "original_level": level, "source": "advanced_words_curated"})
    return out


def parse_r_file(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"const R=(\[.*?\]);const A=", text, re.S)
    if not m:
        raise RuntimeError(f"cannot parse {path.name}")
    rows = json.loads(m.group(1))
    out = []
    for x in rows:
        if not isinstance(x, list) or len(x) < 4:
            continue
        level, reading, display, meaning = (str(x[i] or "") for i in range(4))
        if reading and display and meaning and level in VALID:
            out.append({"reading": reading, "display": display, "meaning": meaning,
                        "original_level": level, "source": path.stem})
    return out


def parse_common_fixups() -> list[dict]:
    text = COMMON_FIXUPS.read_text(encoding="utf-8")
    pat = re.compile(
        r"\{id:'[^']*',level:'(N[1-5])',reading:'([^']+)',kanji:'([^']*)',"
        r"displayWord:'([^']*)',meaning:'([^']*)'"
    )
    out = []
    for level, reading, kanji, display, meaning in pat.findall(text):
        out.append({"reading": reading, "display": display or kanji or reading,
                    "meaning": meaning, "original_level": level, "source": "vocab_common_fixups"})
    if not out:
        raise RuntimeError("cannot parse vocab_common_fixups.js")
    return out


def load_supplements() -> tuple[list[dict], dict[str, list[str]]]:
    rows = parse_curated()
    for path in SUPPLEMENT_R_FILES:
        rows.extend(parse_r_file(path))
    rows.extend(parse_common_fixups())
    by_key: dict[str, dict] = {}
    sources: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        k = key(r["reading"], r["display"])
        sources[k].append(r["source"])
        if k not in by_key:
            x = dict(r); x["key"] = k
            by_key[k] = x
    return list(by_key.values()), {k: sorted(set(v)) for k, v in sources.items()}


def load_existing_audit() -> list[dict]:
    with TEACHER_TSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def resolve_tomoshi(conn: sqlite3.Connection, row: dict, entry_info: dict,
                    tomoshi_jlpt: dict, common_map: dict, ranks: dict) -> dict:
    display, reading = row["display"], row["reading"]
    candidates = []
    for eid, form_common in conn.execute("SELECT entry_id,is_common FROM forms WHERE text=?", (display,)):
        eid = str(eid)
        info = entry_info.get(eid) or {}
        readings = {v1.norm(x) for x in (info.get("readings") or set())}
        if v1.norm(reading) not in readings:
            continue
        candidates.append((eid, bool(form_common), bool(common_map.get(eid) or info.get("common"))))
    # Deduplicate candidate IDs; ambiguity is exposed instead of guessed away.
    best_by_id = {}
    for eid, form_common, common in candidates:
        old = best_by_id.get(eid, (False, False))
        best_by_id[eid] = (old[0] or form_common, old[1] or common)
    candidates = [(eid, x[0], x[1]) for eid, x in best_by_id.items()]
    level_values = set()
    level_sources = []
    for eid, _fc, _co in candidates:
        if eid in tomoshi_jlpt:
            lvl, source = tomoshi_jlpt[eid]
            if lvl in VALID:
                level_values.add(lvl); level_sources.append(f"{eid}:{source}:{lvl}")
        else:
            lvl = str((entry_info.get(eid) or {}).get("jlpt") or "")
            if lvl in VALID:
                level_values.add(lvl); level_sources.append(f"{eid}:entry:{lvl}")
    rank_values = [ranks[eid] for eid, _fc, _co in candidates if eid in ranks]
    return {
        "entry_ids": [x[0] for x in candidates],
        "ambiguous_entry": len(candidates) > 1,
        "common": any(x[1] or x[2] for x in candidates),
        "rank": min(rank_values) if rank_values else None,
        "level": next(iter(level_values)) if len(level_values) == 1 else "",
        "level_conflict": sorted(level_values),
        "level_sources": level_sources,
    }


def one(mapping: dict, k: str) -> str:
    vals = mapping.get(k) or set()
    vals = {x for x in vals if x in VALID}
    return next(iter(vals)) if len(vals) == 1 else ""


def choose_direct(row: dict, ev: dict[str, str]) -> tuple[str, str, str, bool]:
    k = row["key"]
    if k in v4.TEACHER_ANCHORS:
        return v4.TEACHER_ANCHORS[k], "A", "teacher-anchor", False
    if ev.get("manual"):
        return ev["manual"], "A", "manual-secondary-exact", False

    weighted = defaultdict(int)
    sources_by_level = defaultdict(list)
    weights = {
        "core": 6, "openjlpt": 4, "waller": 4, "tomoshi": 3,
    }
    for source, weight in weights.items():
        lvl = ev.get(source, "")
        if lvl in VALID:
            weighted[lvl] += weight
            sources_by_level[lvl].append(source)
    if not weighted:
        return "", "D", "runtime-estimate-required", False
    ordered = sorted(weighted, key=lambda lv: (weighted[lv], -IDX[lv]), reverse=True)
    top = ordered[0]
    conflict = len(weighted) > 1
    if len(ordered) > 1 and weighted[ordered[0]] == weighted[ordered[1]]:
        # Exact-source tie: use the easier of the tied levels as a conservative learner
        # classification rather than promoting a common word without consensus.
        tied = [lv for lv in ordered if weighted[lv] == weighted[top]]
        top = min(tied, key=lambda lv: IDX[lv])
        conflict = True
    corroborators = len(sources_by_level[top])
    if conflict:
        grade = "C"; basis = "runtime-exact-source-conflict"
    elif corroborators >= 2 or weighted[top] >= 7:
        grade = "A"; basis = "+".join(sources_by_level[top]) + "-exact"
    else:
        grade = "B"; basis = sources_by_level[top][0] + "-exact"
    return top, grade, basis, conflict


def direct_rank_medians(existing: list[dict]) -> dict[str, float]:
    values = defaultdict(list)
    for row in existing:
        if row.get("grade") not in {"A", "B", "C"}:
            continue
        try:
            rank = int(row.get("frequency_rank") or 0)
        except Exception:
            continue
        if rank > 0 and row.get("level") in {"N5", "N4", "N3", "N2"}:
            values[row["level"]].append(math.log10(rank))
    medians = {}
    for level, xs in values.items():
        xs.sort()
        n = len(xs)
        medians[level] = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
    return medians


def estimate_level(row: dict, db: dict, medians: dict[str, float]) -> tuple[str, str]:
    original = row.get("original_level") if row.get("original_level") in VALID else "N3"
    # An unsupported N1 tag from a legacy supplement is only a weak prior, never N1
    # evidence. N1 requires direct reusable/manual evidence in this project.
    prior = "N2" if original == "N1" else original
    rank = db.get("rank")
    if isinstance(rank, int) and rank > 0 and medians:
        lr = math.log10(rank)
        candidates = [x for x in ("N5", "N4", "N3", "N2") if x in medians]
        rank_level = min(candidates, key=lambda x: abs(lr - medians[x])) if candidates else prior
        idx = round(0.75 * IDX[rank_level] + 0.25 * IDX[prior])
        idx = min(max(idx, IDX["N5"]), IDX["N2"])
        return v1.LEVELS[idx], "rank-calibrated+legacy-weak-prior"
    if db.get("common") and prior == "N2" and original == "N1":
        return "N3", "common-no-rank+legacy-weak-prior"
    return prior, "legacy-weak-prior-no-direct-evidence"


def write_full_audit(existing: list[dict], added: list[dict]):
    fields = ["reading", "display", "level", "grade", "status", "basis", "common",
              "frequency_rank", "entry_id", "evidence"]
    all_rows = existing + added
    all_rows.sort(key=lambda x: (IDX.get(x.get("level"), 99), x.get("reading", ""), x.get("display", "")))
    with TEACHER_TSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(all_rows)
    return all_rows


def write_overlay(full_rows: list[dict], supplement_keys: set[str], sources: dict[str, list[str]]):
    by_key = {key(r["reading"], r["display"]): r for r in full_rows}
    tuples = []
    for k in sorted(supplement_keys):
        row = by_key.get(k)
        if not row:
            raise RuntimeError(f"supplement key missing from full teacher audit: {k}")
        tuples.append([k, row["level"], row["grade"], row["basis"], row["status"], sources.get(k, [])])
    meta = {
        "version": "20260826-teacher-runtime-v1",
        "generated": datetime.now(timezone.utc).isoformat(),
        "configuredKeys": len(tuples),
        "rule": "apply teacher-audited exact reading+display level after all additive runtime supplements",
    }
    js = (
        "// AUTO-GENERATED exact teacher-level overlay for additive runtime supplements.\n"
        "(()=>{\"use strict\";\n"
        f"const M={json.dumps(meta,ensure_ascii=False,separators=(',',':'))},T={json.dumps(tuples,ensure_ascii=False,separators=(',',':'))};\n"
        "const map=new Map(T.map(x=>[x[0],x]));const A=Array.isArray(window.ADVANCED_WORDS)?window.ADVANCED_WORDS:[];let applied=0,changed=0;\n"
        "for(const w of A){const display=String(w.kanji||w.displayWord||w.reading||'').trim(),reading=String(w.reading||'').trim(),x=map.get(`${reading}|${display}`);if(!x)continue;applied++;if(w.level!==x[1])changed++;w.level=x[1];w.teacherGrade=x[2];w.teacherBasis=x[3];w.estimated=String(x[4]).startsWith('estimated');w.levelSource=`teacher-runtime-overlay:${x[3]}`;}\n"
        "window.VOCAB_TEACHER_RUNTIME_OVERLAY_META={...M,appliedRows:applied,changedRows:changed};\n"
        "})();\n"
    )
    OVERLAY_JS.write_text(js, encoding="utf-8")
    return meta


def main() -> int:
    if not v1.DB.exists():
        raise RuntimeError(f"Tomoshi DB missing: {v1.DB}")
    existing = load_existing_audit()
    existing_keys = {key(r["reading"], r["display"]) for r in existing}
    supplements, source_map = load_supplements()
    supplement_keys = {r["key"] for r in supplements}
    missing = [r for r in supplements if r["key"] not in existing_keys]

    conn = sqlite3.connect(str(v1.DB))
    _zh, entry_info, tomoshi_jlpt, _total = exact.load_tomoshi(conn)
    common_map, ranks = v1.load_db_evidence(conn)
    waller_id, waller_key = v1.load_waller()
    open_key, _open_counts = v1.load_openjlpt()
    manual = v1.load_manual_secondary()
    core_deck = v4.load_core_deck_levels()
    medians = direct_rank_medians(existing)

    added = []
    direct_added = 0
    conflict_added = 0
    for row in missing:
        db = resolve_tomoshi(conn, row, entry_info, tomoshi_jlpt, common_map, ranks)
        eid_levels = {one(waller_id, eid) for eid in db["entry_ids"]}
        eid_levels.discard("")
        waller = one(waller_key, row["key"])
        if not waller and len(eid_levels) == 1:
            waller = next(iter(eid_levels))
        ev = {
            "manual": manual.get(row["key"], ""),
            "core": core_deck.get(row["key"], ""),
            "openjlpt": one(open_key, row["key"]),
            "waller": waller,
            "tomoshi": db.get("level", ""),
        }
        level, grade, basis, conflict = choose_direct({**row, "common": db["common"]}, ev)
        if level:
            status = "direct" + ("+conflict" if conflict else "")
            direct_added += 1
            conflict_added += int(conflict)
        else:
            level, why = estimate_level(row, db, medians)
            grade, basis, status = "D", f"runtime-estimate:{why}", "estimated"
        if level == "N1" and status.startswith("estimated"):
            raise RuntimeError(f"unsupported estimated N1 escaped policy: {row['key']}")
        evidence = {
            "runtimeSources": source_map.get(row["key"], []),
            "legacyLevel": row["original_level"],
            "exactEvidence": {k: v for k, v in ev.items() if v},
            "tomoshiEntryIds": db["entry_ids"],
            "tomoshiAmbiguous": db["ambiguous_entry"],
            "tomoshiLevelConflict": db["level_conflict"],
            "tomoshiLevelSources": db["level_sources"],
        }
        added.append({
            "reading": row["reading"], "display": row["display"], "level": level,
            "grade": grade, "status": status, "basis": basis,
            "common": "1" if db["common"] else "0",
            "frequency_rank": str(db["rank"] or ""),
            "entry_id": db["entry_ids"][0] if len(db["entry_ids"]) == 1 else "",
            "evidence": json.dumps(evidence, ensure_ascii=False, separators=(",", ":")),
        })

    full = write_full_audit(existing, added)
    overlay_meta = write_overlay(full, supplement_keys, source_map)
    counts = Counter(r["level"] for r in full)
    grades = Counter(r["grade"] for r in full)
    estimated_n1 = [key(r["reading"], r["display"]) for r in full
                    if r["level"] == "N1" and r["status"].startswith("estimated")]
    duplicate = len(full) - len({key(r["reading"], r["display"]) for r in full})
    if estimated_n1:
        raise RuntimeError(f"full runtime audit contains estimated N1: {estimated_n1[:20]}")
    if duplicate:
        raise RuntimeError(f"full runtime audit has {duplicate} duplicate exact keys")

    audit = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    runtime = {
        "status": "complete",
        "version": "20260826-teacher-runtime-v1",
        "scope": "all generated core+advanced keys plus every additive runtime vocabulary supplement loaded by advanced_words.js",
        "baseTeacherRows": len(existing),
        "supplementConfiguredUniqueKeys": len(supplement_keys),
        "supplementUniqueKeysAlreadyAudited": len(supplement_keys) - len(missing),
        "supplementUniqueKeysAddedToAudit": len(missing),
        "rowCount": len(full),
        "countsByLevel": {x: counts.get(x, 0) for x in v1.LEVELS},
        "gradeCounts": dict(grades),
        "directSupplementRowsAdded": direct_added,
        "conflictingDirectSupplementRowsAdded": conflict_added,
        "estimatedSupplementRowsAdded": len(missing) - direct_added,
        "estimatedN1": len(estimated_n1),
        "duplicateExactKeys": duplicate,
        "rankLogMediansUsed": medians,
        "overlay": overlay_meta,
        "auditArtifact": "data/jlpt_teacher_audit.tsv",
        "overlayArtifact": "data/vocab_teacher_runtime_overlay.js",
        "officialJlptCaveat": "JLPT does not publish a canonical post-2010 word-by-word vocabulary list; grade D rows are teacher-style study estimates, not official JLPT classifications.",
    }
    audit["runtimeTeacherAudit"] = runtime
    audit.setdefault("policy", {})["runtimeJlptLevel"] = (
        "Every additive runtime vocabulary exact key is reconciled to the teacher audit. "
        "Unsupported legacy N1 estimates are forbidden; N1 requires direct evidence."
    )
    # Keep the base v4 metadata honest while pointing to the extended artifact size.
    audit.setdefault("jlptRecalibration", {})["runtimeExtendedAuditRows"] = len(full)
    AUDIT_JSON.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(runtime, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
