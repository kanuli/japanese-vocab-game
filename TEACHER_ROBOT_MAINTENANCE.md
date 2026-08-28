# Japanese Teacher + Robot Maintenance Policy

## Purpose

The website is maintained by two cooperating layers.

### 1. Japanese Teacher layer

The Teacher is responsible for linguistic correctness and educational quality across every section:

- vocabulary / word list / word audio
- grammar
- listening
- conversation
- pronunciation and furigana
- mock tests
- translator / speech support

The Teacher must research current authoritative Japanese-language resources worldwide and compare useful changes with the repository. A source change is a review trigger, not permission to publish automatically.

### 2. Robot layer

The Robot is responsible for deterministic engineering maintenance:

- validate all local HTML resources and duplicate IDs
- validate JavaScript syntax and required runtime integration
- validate learning-data invariants and hosted audio catalogs
- run Chromium smoke tests across all pages
- verify the deployed GitHub Pages site
- publish machine-readable health status only from real test outcomes
- detect stale or version-pinned validator rules
- watch authoritative source pages for changes

The Robot must never turn a failed check green by editing a status file manually.

## Authority hierarchy

Use sources in this order when reviewing language data:

1. JLPT official website (Japan Foundation / JEES) for exam structure, level competence descriptions and official sample formats.
2. Japan Foundation JF Standard / Can-do / Marugoto / Irodori / Erin materials for communicative competence, everyday scenarios and teaching design.
3. EDRDG JMdict for dictionary readings, spellings, parts of speech and lexical sense cross-checks, subject to its licence.
4. NINJAL corpora, including BCCWJ/BCCWJ2, for contemporary usage and frequency/context evidence.
5. University of Tokyo OJAD for pitch-accent and pronunciation reference.
6. Other reputable dictionaries/corpora only as secondary evidence.

## JLPT level rule

The JLPT does not provide a complete official vocabulary list for N1-N5. Therefore:

- never label a third-party vocabulary level as `official`;
- preserve `推定` / estimated status where the level is inferred;
- require multiple evidence signals for broad level reassignment;
- exact teacher-reviewed overrides take precedence over bulk heuristics;
- conflicting evidence must be queued for teacher review instead of silently overwritten.

## Automatic publication rules

The Robot MAY automatically publish:

- engineering fixes that restore deterministic validators without weakening coverage;
- broken local-resource references where the intended current resource is unambiguous;
- generated health/source-watch status files;
- cache/version changes that do not alter language content.

The Robot MUST NOT automatically publish substantive language changes solely because an external source changed. Vocabulary meanings, JLPT estimates, grammar explanations, conversation text, translations, furigana and pronunciation mappings require Teacher review plus regression tests.

## Teacher review gates

A database change is publishable only when all applicable checks pass:

1. Japanese form / reading is valid.
2. Traditional Chinese meaning is sense-appropriate, not copied from an unrelated homophone.
3. Part of speech and usage constraints are coherent.
4. JLPT label is either source-backed or explicitly estimated.
5. Duplicate exact keys do not conflict.
6. Furigana maps the actual written form correctly.
7. Audio lookup resolves the same reading shown to the learner.
8. Affected page passes browser smoke testing.
9. Full site maintenance passes Static + Data + Browser + Live.

## Recurrence prevention

The maintenance workflow must avoid exact cache-buster assertions such as requiring `file.js?v=YYYYMMDD...`. Validators should identify the resource semantically (for example, exactly one load of `file.js`) and allow the cache token to evolve.

Validator file lists must not keep deleted legacy resources as mandatory dependencies. Page references and data invariants should be the source of truth wherever possible.

## Source-watch policy

`teacher-source-watch.json` defines the authoritative sources monitored by the Robot. `teacher-source-status.json` is generated automatically.

- `ok`: source reachable and no detected source-signature change requiring review.
- `review_required`: one or more monitored source signatures changed since the previous successful check.
- `error`: one or more authoritative sources could not be checked.

A `review_required` state is not a website outage. It means the Teacher should inspect the changed source and decide whether any database section should be improved.
