#!/usr/bin/env python3
import csv
import json
import re
from collections import OrderedDict
from pathlib import Path

INLINE_RE = re.compile(r"\[[ぁ-ゖァ-ヺー]+\]")
AUDIT = Path("data/jlpt_teacher_audit.tsv")
REPORT = Path("data/inline_reading_cleanup_report.json")
CATALOGS = [
    Path("word-supertonic3-catalog.json"),
    Path("word-voicevox-catalog.json"),
    Path("word-aivis-catalog.json"),
]
OPTIONAL_JSON = [Path("data/vocab_audit.json")]


def clean_inline(value: str) -> str:
    return INLINE_RE.sub("", value or "")


def truthy(value: str) -> int:
    return 1 if str(value or "").strip().lower() in {"1", "true", "yes", "y"} else 0


def row_rank(row):
    grade = str(row.get("grade") or row.get("teacherGrade") or "").strip().upper()
    status = str(row.get("status") or row.get("teacherStatus") or "").strip().lower()
    display = str(row.get("display") or "").strip()
    return (
        1 if not INLINE_RE.search(display) else 0,
        3 if grade == "A" else 2 if grade == "B" else 1 if grade == "C" else 0,
        2 if status == "direct" else 1 if status else 0,
        truthy(row.get("common") or row.get("teacherCommon")),
        sum(1 for v in row.values() if str(v or "").strip()),
    )


def merge_rows(rows, fieldnames):
    canonical = dict(max(rows, key=row_rank))
    for row in rows:
        for field in fieldnames:
            if not str(canonical.get(field) or "").strip() and str(row.get(field) or "").strip():
                canonical[field] = row[field]
    canonical["display"] = clean_inline(str(canonical.get("display") or "").strip())
    return canonical


def normalize_audit():
    with AUDIT.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        if not reader.fieldnames or "reading" not in reader.fieldnames or "display" not in reader.fieldnames:
            raise SystemExit(f"Unexpected audit header: {reader.fieldnames}")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    malformed = []
    groups = OrderedDict()
    display_map = OrderedDict()
    for idx, row in enumerate(rows):
        reading = str(row.get("reading") or "").strip()
        display = str(row.get("display") or "").strip() or reading
        if not reading or not display:
            raise SystemExit(f"Blank lexical key at row {idx + 2}")
        clean = clean_inline(display)
        if clean != display:
            malformed.append({"reading": reading, "display": display, "cleanDisplay": clean})
            display_map[display] = clean
        key = reading + "|" + clean
        groups.setdefault(key, []).append(row)

    merged = []
    conflict_groups = []
    duplicate_groups = 0
    duplicate_rows_removed = 0
    for key, group in groups.items():
        if len(group) > 1:
            duplicate_groups += 1
            duplicate_rows_removed += len(group) - 1
            important = [
                x for x in ("teacherLevel", "level", "meaning", "meaningTC", "traditionalChinese", "grade", "teacherGrade", "status", "teacherStatus")
                if x in fieldnames
            ]
            conflicts = {}
            for field in important:
                vals = sorted({str(r.get(field) or "").strip() for r in group if str(r.get(field) or "").strip()})
                if len(vals) > 1:
                    conflicts[field] = vals
            if conflicts:
                conflict_groups.append({"key": key, "conflicts": conflicts})
        merged.append(merge_rows(group, fieldnames))

    seen = set()
    for row in merged:
        reading = str(row.get("reading") or "").strip()
        display = str(row.get("display") or "").strip() or reading
        key = reading + "|" + display
        if INLINE_RE.search(reading + display):
            raise SystemExit(f"Normalization left inline reading: {key}")
        if key in seen:
            raise SystemExit(f"Duplicate key after normalization: {key}")
        seen.add(key)
    if len(merged) < 32000:
        raise SystemExit(f"Normalized audit unexpectedly small: {len(merged)}")

    with AUDIT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(merged)

    return {
        "rowsBefore": len(rows),
        "rowsAfter": len(merged),
        "malformedRows": len(malformed),
        "duplicateGroupsMerged": duplicate_groups,
        "duplicateRowsRemoved": duplicate_rows_removed,
        "metadataConflictGroups": conflict_groups,
        "malformed": malformed,
        "displayMap": display_map,
    }


def migrate_catalog(path: Path):
    if not path.exists():
        return {"file": str(path), "present": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data.get("words") or {}
    migrated = 0
    legacy_collision_aliases = 0
    examples = []
    for old_key in list(words.keys()):
        if "|" not in old_key:
            continue
        reading, display = old_key.split("|", 1)
        clean = clean_inline(display)
        if clean == display:
            continue
        new_key = reading + "|" + clean
        if new_key in words:
            legacy_collision_aliases += 1
            continue
        words[new_key] = words.pop(old_key)
        migrated += 1
        if len(examples) < 20:
            examples.append({"from": old_key, "to": new_key})
    data["words"] = words
    data["canonicalizedInlineReadingKeys"] = migrated
    data["legacyAnnotatedAliasKeys"] = legacy_collision_aliases
    # Key renames do not add/remove recordings, so all count fields remain valid.
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return {
        "file": str(path),
        "present": True,
        "migratedToCleanKey": migrated,
        "legacyCollisionAliasesRetained": legacy_collision_aliases,
        "wordCount": len(words),
        "examples": examples,
    }


def replace_known_strings(obj, display_map):
    if isinstance(obj, dict):
        return {k: replace_known_strings(v, display_map) for k, v in obj.items()}
    if isinstance(obj, list):
        return [replace_known_strings(v, display_map) for v in obj]
    if isinstance(obj, str):
        if obj in display_map:
            return display_map[obj]
        if "|" in obj:
            reading, display = obj.split("|", 1)
            if display in display_map:
                return reading + "|" + display_map[display]
        return obj
    return obj


def normalize_optional_json(display_map):
    changed = []
    for path in OPTIONAL_JSON:
        if not path.exists():
            continue
        before = path.read_text(encoding="utf-8")
        data = json.loads(before)
        data = replace_known_strings(data, display_map)
        after = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed.append(str(path))
    return changed


def main():
    report = normalize_audit()
    display_map = report["displayMap"]
    report["catalogs"] = [migrate_catalog(p) for p in CATALOGS]
    report["normalizedJsonFiles"] = normalize_optional_json(display_map)
    report["policy"] = (
        "Canonical clean lexical rows are preferred; malformed duplicates are merged into the clean key; "
        "missing fields are filled from duplicates; audio catalog keys are renamed only when no clean key exists, "
        "preserving the same wid/shard and all existing recordings."
    )
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "rowsBefore": report["rowsBefore"],
        "rowsAfter": report["rowsAfter"],
        "malformedRows": report["malformedRows"],
        "duplicateRowsRemoved": report["duplicateRowsRemoved"],
        "metadataConflictGroupCount": len(report["metadataConflictGroups"]),
        "catalogs": report["catalogs"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
