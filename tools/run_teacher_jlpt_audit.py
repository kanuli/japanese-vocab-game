#!/usr/bin/env python3
"""Entrypoint for the source-lineage-aware JLPT teacher audit v5."""
from __future__ import annotations

import recalibrate_jlpt_teacher_v4 as v4
import teacher_jlpt_policy_v5 as v5
import teacher_manual_review as manual_review

manual_review.install()
v5.install()

if __name__ == "__main__":
    raise SystemExit(v4.main())