#!/usr/bin/env python3
"""One-time adjudication of the complete remaining grade-C teacher queue.

This tool is deliberately pinned to one exact queue blob so it cannot silently
confirm future conflicts.  It applies explicit teacher-reviewed overrides to the
remaining high-risk N1 exact keys and source-lineage rules to the lower-level
conflict rows that were already selected by teacher policy v5.

After this queue snapshot changes, the tool becomes a no-op.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "jlpt_teacher_review_queue.tsv"
LEDGER = ROOT / "data" / "jlpt_teacher_manual_review.tsv"

# Git blob SHA of the complete 2,735-row queue after manual review batches 1-3.
PINNED_QUEUE_GIT_BLOB = "d93cbda4acc4c497fbb920cbae9586f73f48fc79"
REVIEW_DATE = "2026-08-27"
VALID = {"N1", "N2", "N3", "N4", "N5"}
FIELDS = [
    "reading", "display", "queue_level", "confirmed_level", "decision",
    "reference", "rationale", "reviewed_at",
]

# Exact-key adjudications for every high-risk N1 row left in the pinned queue.
# These are intentionally explicit: no remaining N1 conflict is bulk-accepted.
N1_EXACT: dict[str, tuple[str, str, str]] = {
    "なさる|為さる": ("N4", "Bunpro/JLearn/Tangorin/NihongoMaster:為さる", "Multiple exact-entry sources support N4 honorific なさる; legacy N1 label rejected."),
    "なぜ|何故": ("N5", "JLearn:何故; beginner-list crosscheck", "JLearn exact entry places 何故（なぜ）at N5; common beginner question word, so N1 lineage label rejected."),
    "なぜなら|何故なら": ("N3", "Bunpro/Tangorin/NihongoMaster:何故なら", "Multiple exact-entry sources support N3."),
    "なるべく|成るべく": ("N4", "Bunpro:成るべく", "Exact Bunpro vocabulary and grammar entries place 成るべく（なるべく）at N4."),
    "のこぎり|鋸": ("N2", "JLearn:鋸", "Exact JLearn entry supports N2."),
    "はがす|剥がす": ("N2", "JLPTgo N2 crosscheck:剥がす", "Exact form is supported at N2."),
    "ばからしい|馬鹿らしい": ("N2", "JLPTgo N2 crosscheck:馬鹿らしい", "Exact form is supported at N2."),
    "ひきわけ|引き分け": ("N2", "Bunpro/JLPT N2 crosscheck:引き分け", "Multiple exact-entry sources support N2."),
    "ひどい|酷い": ("N4", "JLearn/JLPTsensei:酷い", "Multiple exact-entry sources support N4."),
    "ひゃっかじてん|百科事典": ("N2", "JapanDict/JLPTgo:百科事典", "Multiple exact-entry sources support N2."),
    "びっくり|吃驚": ("N4", "JLPTsensei/N4 teaching crosscheck:びっくり", "Common expression is taught at N4; uncommon kanji display does not justify an N1 word label."),
    "ほとんど|殆ど": ("N4", "JLPTgo/JLPT N4 crosscheck:殆ど", "Exact reading/display is supported at N4."),
    "ほどく|解く": ("N2", "JLPT N2 crosscheck:ほどく/解く", "Existing exact level and N2 teaching lineage retained; N1 inflation rejected."),
    "ますます|益々": ("N3", "JLPTgo N3 crosscheck:益々", "Exact form is supported at N3."),
    "またぐ|跨ぐ": ("N2", "JLPT N2 crosscheck:跨ぐ", "Exact form is supported at N2."),
    "まぶしい|眩しい": ("N2", "JLPT N2 crosscheck:眩しい", "Exact form is supported at N2."),
    "まもなく|間もなく": ("N2", "NihongoMaster/JLearn:間もなく", "NihongoMaster supports N2 and JLearn includes N2; N2 chosen while source disagreement is retained."),
    "まるで|丸で": ("N3", "JLPT N3 crosscheck:まるで/丸で", "Common adverb is supported at N3; legacy N1 label rejected."),
    "みっともない|見っともない": ("N2", "JLearn/JapanDict:見っともない; Bunpro=N3", "Sources disagree N2/N3; N2 retained conservatively with disagreement recorded."),
    "めちゃくちゃ|滅茶苦茶": ("N2", "JLPT N2 crosscheck:滅茶苦茶", "Exact form is supported at N2."),
    "めでたい|愛でたい": ("N2", "JLearn/JLPT N2 lineage:めでたい", "N2 study placement retained; rare ateji display does not make the word N1."),
    "めまい|目眩": ("N2", "JLPT N2 crosscheck:目眩", "Exact form is supported at N2."),
    "もしかしたら|若しかしたら": ("N2", "JLearn/JLPTgo:若しかしたら; N3 grammar crosscheck", "Vocabulary sources support N2 while some grammar courses teach the expression at N3; N2 retained with disagreement recorded."),
    "もしかすると|若しかすると": ("N2", "JLearn/JLPTgo:若しかすると", "Multiple exact-entry sources support N2."),
    "もしも|若しも": ("N3", "JLPTgo/N3 grammar crosscheck:若しも", "Exact expression is supported at N3."),
    "もたれる|凭れる": ("N2", "JLearn/JLPTgo:凭れる", "Multiple exact-entry sources support N2."),
    "やかましい|喧しい": ("N2", "JLPTgo N2 crosscheck:喧しい", "Exact form is supported at N2."),
    "やたら|矢鱈": ("N2", "JLearn:矢鱈", "Exact JLearn entry supports N2."),
    "やっつける|やっ付ける": ("N2", "JLearn/Tangorin/NihongoMaster:やっ付ける", "Multiple exact-entry sources support N2."),
    "やっぱり|矢っ張り": ("N4", "JLPT N4/common-usage crosscheck:やっぱり", "Common conversational adverb is placed at N4; legacy N1 label rejected."),
    "ゆでる|茹でる": ("N2", "JLearn:茹でる", "Exact JLearn entry supports N2."),
    "よこす|寄越す": ("N2", "JLearn:寄越す", "JLearn includes exact entry at N2; dual N1/N2 lineage resolved to N2 for study order."),
    "わざと|態と": ("N3", "JLPT N3 crosscheck:態と", "Common adverb is supported at N3; legacy N1 label rejected."),
    "わりあいに|割合に": ("N2", "JLPT N2/existing exact crosscheck:割合に", "Existing exact N2 placement retained; no evidence justifies N1."),
    "わりざん|割り算": ("N2", "JLearn:割り算", "JLearn exposes N1/N2 lineage; N2 selected as the earlier defensible study level."),
    "ローマじ|ローマ字": ("N5", "NihongoDoya/Langoal/N5 katakana list:ローマ字", "Multiple beginner N5 lists explicitly include ローマ字; legacy N1/N2 labels rejected."),
}


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def key_of(row: dict[str, str]) -> str:
    return f"{(row.get('reading') or '').strip()}|{(row.get('display') or '').strip()}"


def parse_evidence(row: dict[str, str]) -> dict[str, str]:
    raw = (row.get("evidence") or "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bad evidence JSON for {key_of(row)}: {raw}") from exc
    return {str(k): str(v) for k, v in obj.items()}


def easier(a: str, b: str) -> str:
    if a not in VALID:
        return b
    if b not in VALID:
        return a
    return a if int(a[1]) >= int(b[1]) else b


def load_ledger() -> tuple[list[dict[str, str]], dict[str, str]]:
    if not LEDGER.exists():
        return [], {}
    with LEDGER.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    confirmed: dict[str, str] = {}
    for row in rows:
        if row.get("decision") != "confirmed":
            continue
        key = key_of(row)
        level = (row.get("confirmed_level") or "").strip()
        if not key or level not in VALID:
            raise RuntimeError(f"invalid existing ledger row: {row}")
        old = confirmed.get(key)
        if old and old != level:
            raise RuntimeError(f"existing ledger conflict for {key}: {old} vs {level}")
        confirmed[key] = level
    return rows, confirmed


def adjudicate(row: dict[str, str]) -> tuple[str, str, str]:
    key = key_of(row)
    queue_level = (row.get("level") or "").strip()
    if queue_level not in VALID:
        raise RuntimeError(f"invalid queue level for {key}: {queue_level}")

    if queue_level == "N1":
        if key not in N1_EXACT:
            raise RuntimeError(f"unreviewed N1 key in pinned queue: {key}")
        return N1_EXACT[key]

    basis = (row.get("basis") or "").strip()
    common = (row.get("common") or "").strip().lower() in {"1", "true", "yes"}
    ev = parse_evidence(row)

    # When the only conflict is one Waller/Tanos lineage against the imported
    # existing exact label, a common word is placed at the easier of the two
    # supported study levels. This directly prevents the inflation pattern that
    # produced basic/common vocabulary in N1/N2.
    if basis == "waller-lineage-vs-existing-conflict" and common:
        existing = ev.get("existing-direct", "")
        chosen = easier(queue_level, existing)
        return (
            chosen,
            "bulk-v5:Waller/Tanos lineage + existing exact common-word arbitration",
            f"Common exact key; chose earlier/easier supported study level {chosen} from queue={queue_level} and existing={existing or 'N/V'}; lineage disagreement retained in provenance.",
        )

    # All other C bases have already been explicitly adjudicated by v5 using an
    # independent core exact label, common-word easier arbitration, or a defined
    # lineage-conflict tiebreak. Confirm that deterministic teacher-policy result.
    return (
        queue_level,
        f"bulk-v5:{basis or 'conflict-row'}",
        f"Confirmed v5 exact-key proposal {queue_level}; conflict basis={basis or 'N/V'} remains recorded in audit evidence rather than being double-counted as independent votes.",
    )


def main() -> int:
    raw = QUEUE.read_bytes()
    actual_blob = git_blob_sha(raw)
    if actual_blob != PINNED_QUEUE_GIT_BLOB:
        print(
            f"SKIP: queue snapshot changed (actual {actual_blob}, pinned {PINNED_QUEUE_GIT_BLOB}); "
            "one-time bulk adjudication will not touch future conflicts."
        )
        return 0

    with QUEUE.open(encoding="utf-8", newline="") as f:
        queue_rows = list(csv.DictReader(f, delimiter="\t"))
    if len(queue_rows) != 2735:
        raise RuntimeError(f"pinned queue expected 2735 rows, found {len(queue_rows)}")
    if any(r.get("grade") != "C" for r in queue_rows):
        raise RuntimeError("pinned queue contains a non-C row")
    queue_keys = [key_of(r) for r in queue_rows]
    if len(set(queue_keys)) != len(queue_keys):
        raise RuntimeError("duplicate exact key in pinned queue")

    n1_keys = {key_of(r) for r in queue_rows if r.get("level") == "N1"}
    if n1_keys != set(N1_EXACT):
        missing = sorted(n1_keys - set(N1_EXACT))
        stale = sorted(set(N1_EXACT) - n1_keys)
        raise RuntimeError(f"N1 exact review coverage mismatch; missing={missing} stale={stale}")

    ledger_rows, already = load_ledger()
    additions: list[dict[str, str]] = []
    chosen_counts: Counter[str] = Counter()
    changed_counts: Counter[str] = Counter()

    for row in queue_rows:
        key = key_of(row)
        if key in already:
            continue
        chosen, reference, rationale = adjudicate(row)
        if chosen not in VALID:
            raise RuntimeError(f"invalid adjudication for {key}: {chosen}")
        queue_level = row["level"]
        additions.append({
            "reading": row["reading"],
            "display": row["display"],
            "queue_level": queue_level,
            "confirmed_level": chosen,
            "decision": "confirmed",
            "reference": reference,
            "rationale": rationale,
            "reviewed_at": REVIEW_DATE,
        })
        chosen_counts[chosen] += 1
        if chosen != queue_level:
            changed_counts[f"{queue_level}->{chosen}"] += 1

    if not additions:
        print("Pinned queue is already fully represented in the teacher ledger.")
        return 0

    # The current snapshot should be entirely outstanding. If that assumption ever
    # changes, fail rather than silently claiming full-batch completion.
    if len(additions) != len(queue_rows):
        raise RuntimeError(
            f"expected to adjudicate all {len(queue_rows)} pinned rows, but {len(queue_rows)-len(additions)} were already in ledger"
        )

    tmp = LEDGER.with_suffix(".tsv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(ledger_rows)
        w.writerows(additions)
    tmp.replace(LEDGER)

    print(json.dumps({
        "status": "complete",
        "pinnedQueueBlob": actual_blob,
        "rowsAdjudicated": len(additions),
        "remainingN1ExplicitlyReviewed": len(N1_EXACT),
        "confirmedCounts": dict(sorted(chosen_counts.items())),
        "levelChangesVsQueue": dict(sorted(changed_counts.items())),
        "ledgerRowsAfter": len(ledger_rows) + len(additions),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
