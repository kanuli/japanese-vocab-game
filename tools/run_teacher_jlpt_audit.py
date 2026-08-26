#!/usr/bin/env python3
"""Entrypoint for the teacher JLPT audit with externally validated anchor corrections.

These exact-key corrections are deliberately applied at runtime so the full v4 audit
uses the latest teacher validation without depending on broad same-entry inference.
"""
from __future__ import annotations

import recalibrate_jlpt_teacher_v4 as v4

# Targeted secondary validation on 2026-08-26:
# 時雨: 再来月 N5, 再来年 N5, 作る/造る/創る N5, 真ん中 N4,
# 石鹸 N5, 枚 N5.  Only the exact keys present in this database are overridden.
v4.TEACHER_ANCHORS.update({
    "さらいげつ|再来月": "N5",
    "さらいねん|再来年": "N5",
    "つくる|造る": "N5",
})

if __name__ == "__main__":
    raise SystemExit(v4.main())
