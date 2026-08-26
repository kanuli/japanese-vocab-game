# Japanese Learning Content Reference Policy

Version: 2026-08-26

## Purpose

This project may use external Japanese-learning sites as **reference evidence** for coverage, taxonomy, learner difficulty, lexical sense, register, communicative function, and cross-checking. The project must not reproduce proprietary lessons, dictionary records, example sentences, quizzes, explanations, audio, or bulk site databases.

The runtime learning content should be independently written, generated from project-owned templates, or taken from sources whose licences explicitly permit the intended reuse with the required attribution.

## Reference layers

### Layer A — authoritative capability anchor

- JLPT official N1–N5 linguistic-competence descriptions.
- Use these descriptions to decide what a learner at a level should be able to understand in reading/listening and how broad, fast, abstract, or inferential the material may be.
- Do **not** describe any vocabulary or grammar list as an official fixed JLPT list.

### Layer B — user-provided secondary learning references

These are useful for cross-checking and structural coverage, not for copying content:

- Mazii — vocabulary senses, common learner-level labels, part of speech, learner-oriented topic coverage.
- MOJi Dictionary — vocabulary sense / written-form / learner-level cross-check where manually verifiable.
- 時雨日中辭典 — Traditional-Chinese sense cross-check and Japanese usage distinctions.
- U-biq — curriculum progression, grammatical-function progression, and real-life communicative-situation taxonomy.
- 時雨の町 — Traditional-Chinese learner explanations, grammar/conjugation taxonomy, quiz-function taxonomy, and secondary JLPT-style level evidence.

### Layer C — reusable/open evidence already suitable for project tooling

- JMdict / EDRDG-derived lexical data, subject to its licence.
- Tomoshi-linked Traditional-Chinese lexical data already used by this project.
- OpenJLPT as one labelled evidence set, never the sole truth source.
- 5mdld / existing project decks where their licence and provenance permit use.
- Hanabira grammar JSON already used by the project, subject to its repository licence/provenance.
- Tatoeba only when licence/attribution requirements are satisfied. Prefer independently written project sentences when practical.

## Copyright / provenance rules

1. Never bulk scrape Mazii, MOJi, 時雨の町, 時雨日中辭典, U-biq, or another proprietary learning site into the runtime database.
2. Never copy their example sentences, answer choices, explanations, article text, audio, images, or premium records.
3. A grammar pattern name, broad communicative function, or learner-level hypothesis may be used as an evidence signal; the project sentence/question/dialogue must be written independently.
4. When two proprietary sources disagree, do not resolve the disagreement by majority vote alone. Check the official JLPT capability anchor, open evidence, corpus/frequency evidence, morphology/grammar complexity, and actual sentence difficulty.
5. A single proprietary source must never create a hard runtime level assignment.
6. Exact manual cross-checks may be stored only as compact evidence/override records written by the project, not copied dictionary definitions.
7. Audio should be generated from project-owned/appropriately licensed text through the project's approved voice engines; do not reuse website audio unless its licence is explicitly compatible.

## JLPT level model

Because JLPT does not publish a fixed official vocabulary/grammar syllabus, this project uses an evidence model.

### N5

Short, concrete, highly frequent classroom/daily-life material; basic kana/kanji; simple time/place/object relations; short slow listening; direct requests, invitations, preferences, existence, possession, movement and basic sequencing.

### N4

Basic Japanese for familiar daily topics; more subordinate relations and conjugations; conditions, permission/prohibition, ability, experience, purpose, appearance, preparation, comparison, basic passive/potential; listening remains relatively explicit and may be slower than natural speed.

### N3

Bridge level. Coherent everyday discourse at near-natural speed; speaker relationships and main points matter; multi-clause reasoning, change of state/decision, cause/effect, reported information, contrast, viewpoint and pragmatic context become important.

### N2

Everyday plus broader general settings at nearly natural speed; written/general-topic register, indirectness, inference and denser clause relations; grammar and vocabulary may be formal or abstract but should still be common enough in general educated Japanese.

### N1

Broad settings at natural speed; logical/abstract structure, nuanced register, compressed written expressions, formal institutional/business language, subtle inference and writer/speaker intent. **N1 must never be used as a garbage bucket for unknown items.**

## Evidence weighting principles

For vocabulary, retain the repository's existing per-word world-evidence consensus approach. For grammar and generated content, use the following order:

1. official capability compatibility (hard gate for sentence/task difficulty);
2. exact project manual cross-check, when available;
3. agreement across multiple independent learner datasets / reference traditions;
4. open labelled evidence (for example OpenJLPT) and existing project sources;
5. corpus/frequency/register evidence and morphological complexity;
6. model/heuristic estimate only for residual cases.

If evidence is weak or conflicting, keep the item at the less aggressive level or mark it for review instead of forcing N1.

## Page-specific policy

- `index.html`, `wordlist.html`, `wordaudio.html`, vocabulary-plus pages: use the shared calibrated vocabulary layer; do not maintain independent JLPT labels per page.
- `grammar.html`: combine licensed/open grammar coverage with independently written reference-expansion questions and QA for answer uniqueness / grammatical compatibility.
- `listening.html`: balance not only count by N-level, but communicative function, sentence length, speed expectation, information density, indirectness and inference. New scripts must be original.
- `conversation.html`: expand by communicative function and real-world situation, not by superficial noun substitution. Each level should genuinely change syntax, politeness, inference and discourse complexity.
- `mocktest.html`: consume the same calibrated vocabulary/grammar/content pools; do not invent a second conflicting level system.
- `pronunciation.html`: pronunciation material should inherit verified readings from the shared vocabulary/reading layer; quantity is secondary to reading/accent/reference accuracy.
- `translator.html`: it is a utility, not a JLPT database. Do not inflate its database merely to increase counts.

## QA gates for every expansion

- unique Japanese content after normalization;
- exactly one defensible correct answer for multiple-choice items;
- Traditional Chinese explanation/answer contains no unexplained English fallback;
- level-compatible vocabulary, grammar and discourse complexity;
- no template corruption or impossible inflection;
- no answer leakage from option length/format;
- scene/action compatibility;
- no copyright-source sentence similarity introduced intentionally;
- per-level and per-function coverage report before claiming completion.
