# JLPT Vocabulary Coverage Audit

Generated: `2026-08-20T16:51:12.082698+00:00`

This is an **audit-only** report. It does not automatically add, delete, or re-level vocabulary.

## Current runtime inventory

| Layer | Unique entries |
|---|---:|
| Core source (robust parse) | 10,511 |
| Core accepted by current browser parser | 10,511 |
| Curated supplement | 140 |
| Advanced bundle | 11,737 |
| Final merged runtime set | 22,319 |

## External reference inventory

| Source | N5 | N4 | N3 | N2 | N1 |
|---|---:|---:|---:|---:|---:|
| openjlpt | 499 | 491 | 1,567 | 1,498 | 3,183 |
| waller | 684 | 640 | 1,730 | 1,812 | 3,427 |
| wordmaster | 710 | 676 | 2,246 | 3,636 | 2,931 |

## Coverage by level

| Level | Reference entries | Exact | Variant | Missing | Coverage |
|---|---:|---:|---:|---:|---:|
| N5 | 822 | 698 | 34 | 90 | 89.05% |
| N4 | 780 | 655 | 44 | 81 | 89.62% |
| N3 | 2,448 | 2,275 | 43 | 130 | 94.69% |
| N2 | 3,761 | 3,267 | 82 | 412 | 89.05% |
| N1 | 3,955 | 3,163 | 279 | 513 | 87.03% |

## Consensus coverage (recommended metric)

| Level | Consensus entries | Exact | Variant/related | Missing | Coverage |
|---|---:|---:|---:|---:|---:|
| N5 | 627 | 611 | 10 | 6 | 99.04% |
| N4 | 601 | 566 | 32 | 3 | 99.5% |
| N3 | 2,029 | 1,946 | 17 | 66 | 96.75% |
| N2 | 1,497 | 1,352 | 41 | 104 | 93.05% |
| N1 | 2,292 | 2,158 | 21 | 113 | 95.07% |

## Findings

- High-confidence missing (supported by >=2 independent external families): **292**
- Single-source gaps requiring review: **814**
- Level conflicts: **3,276**
- Conservative variant matches: **436**
- Core rows rejected by current runtime parser: **0**
- Core rows rejected and not restored by supplements: **0**

### Sample high-confidence missing entries

| Word | Reading | Consensus | Sources |
|---|---|---|---|
| 暖まる | あたたまる | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| あぶる | あぶる | N2 | community-independent|waller-derived (waller|wordmaster) |
| アワー | アワー | N1 | community-independent|waller-derived (waller|wordmaster) |
| 行き | いき | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| いけない | いけない | N3 | community-independent|waller-derived (waller|wordmaster) |
| いただきます | いただきます | N3 | community-independent|waller-derived (waller|wordmaster) |
| 一斉 | いっせい | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| いってまいります | いってまいります | N2 | community-independent|waller-derived (waller|wordmaster) |
| いつのまにか | いつのまにか | N3 | community-independent|waller-derived (waller|wordmaster) |
| いらっしゃい | いらっしゃい | N3 | community-independent|waller-derived (waller|wordmaster) |
| 魚 | うお | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| うなる | うなる | N3 | community-independent|waller-derived (waller|wordmaster) |
| 産む | うむ | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 売り出し | うりだし | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| うんと | うんと | N2 | community-independent|waller-derived (waller|wordmaster) |
| 運輸 | うんゆ | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 英和 | えいわ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 演ずる | えんずる | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 王女 | おうじょ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 応ずる | おうずる | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| おかけください | おかけください | N2 | community-independent|waller-derived (waller|wordmaster) |
| お先に | おさきに | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 治める | おさめる | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| お産 | おさん | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| お互い | おたがい | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| おつり | おつり | N4 | community-independent|waller-derived (waller|wordmaster) |
| お出掛け | おでかけ | N2 | community-independent|waller-derived (waller|wordmaster) |
| おまちどおさま | おまちどおさま | N2 | community-independent|waller-derived (waller|wordmaster) |
| おまわりさん | おまわりさん | N5 | community-independent|waller-derived (waller|wordmaster) |
| お宮 | おみや | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| お目に掛かる | おめにかかる | N3 | community-independent|waller-derived (waller|wordmaster) |
| 思い掛けない | おもいがけない | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 思いっ切り | おもいっきり | N2 | community-independent|waller-derived (waller|wordmaster) |
| お休み | おやすみ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 泳ぎ | およぎ | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 降ろす | おろす | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 街道 | かいどう | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 反る | かえる | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 顔付き | かおつき | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 係わる | かかわる | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |

### Sample runtime final holes

| Word | Reading | Source level | Reason |
|---|---|---|---|
| — | — | — | — |

## Interpretation

- JLPT does not publish a fixed official vocabulary list for the current test, so level disagreements are expected.
- `missing_high_confidence.csv` is the best candidate list for manual addition review.
- `runtime_missing.csv` is the first place to inspect for actual application bugs.
- `level_conflicts.csv` should be reviewed rather than auto-applied, because external sources frequently disagree.
- `missing_single_source.csv` is intentionally lower confidence and should not be bulk-imported.
