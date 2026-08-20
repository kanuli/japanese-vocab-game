# JLPT Vocabulary Coverage Audit

This audit checks whether the vocabulary that the website can actually load covers common JLPT N5–N1 reference vocabulary.

## Why this exists

A large raw word count does not guarantee coverage. The site has multiple layers:

1. remote JLPT core CSV,
2. browser runtime parser,
3. curated supplement,
4. prebuilt advanced bundle.

A word can exist upstream but still disappear if the browser parser rejects its row while the advanced build excludes it as an existing core word.

## External reference families

The audit deliberately avoids treating every mirror as an independent vote.

- **Waller-derived family**
  - OpenJLPT (`evanclan/OpenJLPT`)
  - Jonathan Waller / Tanos data via `stephenmk/yomitan-jlpt-vocab`
- **Independent community family**
  - `lratusa/wordmaster-wordlists`

OpenJLPT and the Waller CSV are counted as one family for high-confidence missing detection because their vocabulary lineage overlaps.

JLPT does not publish a fixed official vocabulary list for the current examination, so level disagreement is expected and is reported separately rather than auto-corrected.

## Output files

Running:

```bash
python tools/audit_vocab_coverage.py --out audit/vocab/results
```

produces:

- `coverage_summary.json` — machine-readable totals and coverage by level
- `README.md` — human-readable result summary
- `missing_high_confidence.csv` — absent words supported by at least two independent reference families
- `missing_single_source.csv` — lower-confidence gaps requiring manual review
- `level_conflicts.csv` — words present on the site but assigned to a different JLPT level than the family-weighted external consensus
- `variant_matches.csv` — conservative kana / prolonged-sound-mark variant matches
- `runtime_missing.csv` — core rows rejected by the current browser parser, with a flag showing whether another vocabulary layer restores the word
- `source_inventory.csv` — per-source/per-level counts and download errors

## Audit rules

### High-confidence missing

A word is marked high-confidence missing only when:

- it is absent from the website's final runtime vocabulary set, and
- it is present in at least two independent reference families.

### Runtime final hole

A word is marked as a runtime final hole when:

- the robust core parser can identify its word + reading,
- the current `wordaudio-data.js` runtime acceptance rules reject it, and
- neither curated nor advanced vocabulary restores the same exact word + reading key.

### Level conflict

Level conflicts are **review items**, not automatic errors. Modern JLPT has no official published fixed vocabulary list, and third-party sources regularly disagree.

## Safety

The audit is read-only with respect to vocabulary data. It does not add, delete, rewrite, or re-level any word automatically.
