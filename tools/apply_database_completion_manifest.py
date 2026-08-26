#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'data/reference_upgrade_manifest.json'
d=json.loads(p.read_text(encoding='utf-8'))
d['version']='2026-08-27-japanese-database-completion-v1'
d['completion']={
 'grammar':'108 representative project-original reference questions; coverage matrix complete; Batch 8 depth gate validates N2/N3 by grammatical complexity rather than sentence length.',
 'listening':'6,690 project-original catalog rows are 100% quality eligible under structural, near-miss, giveaway, length and language-leakage gates; 273 unique targeted reference-expansion items retain subtype coverage.',
 'conversation':'77 scenes / 1,925 dialogues; all scene/level counts preserved; no exact duplicate pairs, no Chinese-field kana leakage, no known generic 進める misuse, and full-database template concentration gates pass.',
 'finalAudit':'data/database_completion_report.json',
 'scopeNote':'Completion is against current project-defined diagnostic and quality gates, not a claim that JLPT publishes or has an exhaustible official grammar/vocabulary syllabus.'
}
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('database completion manifest applied')
