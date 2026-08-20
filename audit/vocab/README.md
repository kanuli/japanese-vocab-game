# JLPT Vocabulary Coverage Audit — corrected strict surface-form method

This audit checks whether the vocabulary that the website can actually load covers JLPT N5–N1 reference vocabulary.

## Current implementation status — 2026-08-21

The **337 direct-reviewed additions are complete on branch `audit/vocab-coverage-20260821`**.

- Direct-reviewed candidates: **337**
- Automatically materialized into `data/advanced_vocab.js`: **152**
- Reviewed Traditional-Chinese completion layer: **185**
- Combined direct-reviewed coverage: **337 / 337**
- Remaining unresolved direct-reviewed additions: **0**

Authoritative implementation evidence: `results/direct_coverage_completion.json`.

`coverage_additions_deferred.csv` is retained only as the historical list of 185 rows for which the automatic JA→ZH lookup did not find a reliable Traditional-Chinese meaning. Those 185 rows are now implemented through `data/coverage_deferred_manual.js` with canonical data in `data/coverage_manual_meanings.json`; they are **not outstanding work**.

The runtime loader `advanced_words.js` loads the completion layer after `data/advanced_vocab.js`. The strict surface-form audit also includes `data/coverage_manual_meanings.json` in its runtime inventory.

## Critical coverage rule

**A vocabulary item is covered only when the final runtime database contains the same written form + reading.**

Different written forms remain separate learnable items even when:

- they have the same reading (`川 / 河`),
- they are alternative orthographies (`温まる / 暖まる`, `気づく / 気付く`),
- they belong to the same JMdict lexical entry,
- one form is more common than another.

JMdict identity is used only to annotate relationships and quality. It never removes a missing surface form.

## Why this correction exists

The earlier experimental refinement incorrectly treated a same-JMdict-entry form as sufficient coverage. That rule could hide valid missing forms. The old `missing_refined.csv`, `refined_summary.json`, `jmdict_related.csv`, and `README_REFINED.md` are therefore **legacy/deprecated outputs and must not be used for coverage decisions**.

The authoritative corrected outputs are the strict surface-form audit, final quality review, and direct-coverage completion report listed below.

## External reference families

The audit deliberately avoids double-counting mirrors as independent votes.

- **Waller-derived family**
  - OpenJLPT (`evanclan/OpenJLPT`)
  - Jonathan Waller / Tanos data via `stephenmk/yomitan-jlpt-vocab`
- **Independent community family**
  - `lratusa/wordmaster-wordlists`
- **JMdict/Japanese Language Data**
  - used for lexical validity, exact form/reading verification, common-form metadata, parts of speech, and variant relationships
  - JMdict is not treated as a JLPT-level vote

JLPT does not publish a fixed official vocabulary list for the current examination, so level disagreement is reported rather than auto-corrected.

## Authoritative workflow

```bash
python tools/audit_vocab_coverage.py --out audit/vocab/results
python tools/audit_vocab_surface_forms.py --results audit/vocab/results
python tools/review_vocab_missing_quality.py --results audit/vocab/results
```

## Authoritative output files

### Implementation completion

- `direct_coverage_completion.json` — **337/337 direct-reviewed completion status and validation evidence**
- `../../data/coverage_additions.json` — 152 automatically materialized additions
- `../../data/coverage_deferred_manual.js` — 185 reviewed runtime additions
- `../../data/coverage_manual_meanings.json` — canonical Traditional-Chinese meanings for those 185 additions
- `coverage_additions_validation.json` — validation for the 152 additions merged into the generated bundle

### Strict coverage

- `surface_form_summary.json` — strict exact-form totals
- `SURFACE_FORM_AUDIT.md` — strict human-readable summary
- `missing_surface_high_confidence.csv` — exact forms absent from runtime and supported by >=2 independent reference families
- `missing_surface_single_source.csv` — exact forms absent from runtime but supported by only one reference family
- `surface_form_relations.csv` — **all strict missing forms**, including annotations for same-reading/different-writing, same-writing/different-reading, and same-JMdict-entry relationships

### Final quality review

- `quality_review_summary.json` — review totals and decision counts
- `QUALITY_REVIEW.md` — human-readable review summary
- `final_quality_review_all_missing.csv` — every strict missing form reviewed independently
- `quality_review_recommended_add.csv` — ADD / ADD-after-source-check candidates
- `quality_review_manual_or_low_priority.csv` — malformed-source, expression, archaic, rare/dialect, and other manual-review cases

### Runtime diagnostics

- `runtime_missing.csv` — core rows rejected by the current browser parser, including whether another vocabulary layer restores them
- `level_conflicts.csv` — level disagreements; review only, never auto-apply
- `source_inventory.csv` — source counts and download errors

## Quality-review principles

1. Exact written form + reading is the unit being audited.
2. `河` is missing if `川` exists but `河` does not.
3. `暖まる` is missing if `温まる` exists but `暖まる` does not.
4. `気付く` is missing if `気づく` exists but `気付く` does not.
5. The same rule is applied automatically to **every** reference item, not only these examples.
6. High-confidence reference support plus an exact JMdict form is strong addition evidence.
7. Fixed expressions/conjugated forms are separated from base-form vocabulary review.
8. Archaic, obsolete, rare, dialectal, malformed, or unresolved source rows are not bulk-added.
9. JLPT level conflicts are flagged for review rather than silently re-leveled.

## Safety and implementation separation

The audit/review scripts themselves are analytical and do not silently rewrite the production vocabulary database. Reviewed implementation is stored explicitly in the generated bundle and the separate completion layer described above. The production `main` branch is not changed by this audit branch unless it is deliberately merged/published.
