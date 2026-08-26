# Vocabulary data notice

The generated vocabulary data in this directory combines multiple open learning/dictionary sources. It is data content, separate from the application source code.

## Tomoshi dictionary data

`advanced_vocab.js` and `vocab_core_verified.js` use Traditional-Chinese definitions and JLPT-related metadata from the open database published by **tomoshi-app/tomoshi-dict-data**, pinned by the build workflow to release **v2026-08-12**.

Source: https://github.com/tomoshi-app/tomoshi-dict-data

The Tomoshi open database identifies its open dictionary data under **CC BY-SA 4.0** and is derived in part from JMdict/JMdictDB data. Redistribution and adaptations of that data should preserve the applicable attribution/share-alike requirements.

License: https://creativecommons.org/licenses/by-sa/4.0/

## Japanese Language Data / JMdict IDs

The build uses `jkindrix/japanese-language-data` to obtain normalized JMdict entries, stable JMdict entry IDs, JLPT Waller annotations when available, and subtitle-frequency enrichment used only as a final estimated-level fallback.

Source: https://github.com/jkindrix/japanese-language-data

## JLPT core deck

The runtime core inventory originates from `5mdld/anki-jlpt-decks` (egg rolls JLPT N1–N5). The generated `vocab_core_verified.js` is an overlay that rechecks its Traditional-Chinese meanings and learning levels using structured dictionary data; unresolved rows retain the core deck value rather than accepting an ambiguous automatic match.

Source: https://github.com/5mdld/anki-jlpt-decks

## Important JLPT note

The post-2010 JLPT does not publish an official per-word N1–N5 vocabulary list. N1–N5 values in this project are learning labels drawn from third-party datasets or, where explicitly indicated by the build metadata, an estimate. They must not be represented as an official JLPT vocabulary list.
