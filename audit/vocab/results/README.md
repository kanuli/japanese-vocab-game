# JLPT Vocabulary Coverage Audit

Generated: `2026-08-20T16:46:38.668813+00:00`

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
| N5 | 822 | 698 | 0 | 124 | 84.91% |
| N4 | 780 | 655 | 0 | 125 | 83.97% |
| N3 | 2,448 | 2,275 | 1 | 172 | 92.97% |
| N2 | 3,761 | 3,267 | 1 | 493 | 86.89% |
| N1 | 3,955 | 3,163 | 4 | 788 | 80.08% |

## Findings

- High-confidence missing (supported by >=2 independent external families): **411**
- Single-family gaps requiring review: **1,126**
- Level conflicts: **3,046**
- Conservative variant matches: **5**
- Core rows rejected by current runtime parser: **0**
- Core rows rejected and not restored by supplements: **0**

### Sample high-confidence missing entries

| Word | Reading | Consensus | Sources |
|---|---|---|---|
| 敢えて | あえて | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 飽くまで | あくまで | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 朝御飯 | あさごはん | N5 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 暖まる | あたたまる | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| あぶる | あぶる | N2 | community-independent|waller-derived (waller|wordmaster) |
| 在る | ある | N5 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| アワー | アワー | N1 | community-independent|waller-derived (waller|wordmaster) |
| 案内 | あんないする | N4 | community-independent|waller-derived (openjlpt|wordmaster) |
| 行き | いき | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| いけない | いけない | N3 | community-independent|waller-derived (waller|wordmaster) |
| いただきます | いただきます | N3 | community-independent|waller-derived (waller|wordmaster) |
| 一斉 | いっせい | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| いってまいります | いってまいります | N2 | community-independent|waller-derived (waller|wordmaster) |
| いつのまにか | いつのまにか | N3 | community-independent|waller-derived (waller|wordmaster) |
| いらっしゃい | いらっしゃい | N3 | community-independent|waller-derived (waller|wordmaster) |
| 入口 | いりぐち | N5 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 居る | いる | N5 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 煎る | いる | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| ウエートレス | ウエートレス | N2 | community-independent|waller-derived (waller|wordmaster) |
| 魚 | うお | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 浮ぶ | うかぶ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 受取 | うけとり | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 打合せ | うちあわせ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 空ろ | うつろ | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| うなる | うなる | N3 | community-independent|waller-derived (waller|wordmaster) |
| 産む | うむ | N3 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 売上 | うりあげ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 売り出し | うりだし | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 売行き | うれゆき | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 運転 | うんてんする | N4 | community-independent|waller-derived (openjlpt|wordmaster) |
| うんと | うんと | N2 | community-independent|waller-derived (waller|wordmaster) |
| 運動 | うんどうする | N4 | community-independent|waller-derived (openjlpt|wordmaster) |
| 運輸 | うんゆ | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 英和 | えいわ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 演ずる | えんずる | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 遠慮 | えんりょする | N4 | community-independent|waller-derived (openjlpt|wordmaster) |
| 於いて | おいて | N1 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 王女 | おうじょ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 応ずる | おうずる | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |
| 大凡 | おおよそ | N2 | community-independent|waller-derived (openjlpt|waller|wordmaster) |

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
