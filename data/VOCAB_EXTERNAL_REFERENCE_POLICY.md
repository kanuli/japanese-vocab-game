# External vocabulary reference policy

The project may consult the following learner dictionaries as **secondary manual validation references**:

- Mazii (Traditional Chinese): https://mazii.net/zh-TW
- MOJi辞書: https://www.mojidict.com/
- 時雨日中辭典: https://www.sigure.tw/dict/jp/

## What this project may use them for

- Confirm that a Japanese surface form/reading is genuinely polysemous.
- Cross-check a likely JLPT-style learner level for an already-known lexical sense.
- Cross-check part of speech, common written form, or whether two spellings represent different senses.
- Help a human reviewer decide which **open JMdict/Tomoshi entry_id** is the right match.

## What this project must not do

- Do not bulk scrape or mirror these websites.
- Do not copy their dictionary definitions, examples, audio, images, premium explanations, or proprietary database records into this repository.
- Do not treat a single proprietary learner dictionary as an authoritative bulk source.
- Do not automatically resolve an ambiguous row merely because one external site returns a first-ranked result.

MOJi's published terms prohibit obtaining platform content/data through crawlers, scripts, robots or similar automated tools without prior written permission. 時雨の町's published terms prohibit unauthorized copying, adaptation, reuse, or programmatic use of site content. No public bulk-data reuse licence was identified for Mazii during this review. Therefore these sites are validation references only.

## Data actually stored here

Runtime meanings remain based on open/redistributable sources (primarily JMdict-linked Tomoshi zh-TW data) or concise independently written manual corrections. External dictionaries can support a review decision, but their wording is not imported.

When a secondary reference confirms a high-confidence unresolved core sense, the exact `reading|display` key may be placed in `data/vocab_external_crosscheck.js`. Ambiguous entries such as `コート|コート` are intentionally left unresolved unless the core source supplies enough sense context to distinguish the entry safely.
