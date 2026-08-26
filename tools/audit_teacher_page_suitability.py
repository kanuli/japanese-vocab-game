from pathlib import Path
import csv, json, re

ROOT=Path('.')
PAGES=['index.html','wordaudio.html','wordlist.html','grammar.html','listening.html','conversation.html','pronunciation.html','mocktest.html','translator.html','vocab-plus-game.html','vocabulary-plus.html']
fail=[]
page_status={}

def load_json(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))

# 1) Page inventory and level-mode classification.
for name in PAGES:
    p=ROOT/name
    if not p.exists():
        fail.append(f'missing page: {name}'); continue
    s=p.read_text(encoding='utf-8')
    page_status[name]={
        'exists':True,
        'hasN1N5':all(x in s for x in ['N1','N2','N3','N4','N5']),
        'teacherVocabLoader':'advanced_words.js' in s,
        'language':'zh-Hant' if 'lang="zh-Hant"' in s else 'other'
    }
    if 'lang="zh-Hant"' not in s: fail.append(f'{name}: page language is not zh-Hant')

# Pages whose level selector is driven by the canonical teacher-calibrated vocabulary runtime.
vocab_pages=['index.html','wordaudio.html','wordlist.html','vocab-plus-game.html','vocabulary-plus.html','mocktest.html']
for name in vocab_pages:
    s=(ROOT/name).read_text(encoding='utf-8')
    if 'advanced_words.js' not in s:
        fail.append(f'{name}: canonical advanced_words teacher chain missing')

mock_html=(ROOT/'mocktest.html').read_text(encoding='utf-8')
mock_js=(ROOT/'mocktest.js').read_text(encoding='utf-8')
if 'wordaudio-data.js' not in mock_html: fail.append('mocktest.html: canonical WA runtime loader missing')
if 'function teacherRuntimeVocab()' not in mock_js or "source:'teacher-runtime'" not in mock_js:
    fail.append('mocktest.js: teacher runtime is not primary vocabulary source')
if '5mdld/anki-jlpt-decks 只在本地教師題庫無法載入時作備援' not in mock_html:
    fail.append('mocktest.html: source disclosure does not identify external deck as fallback')

# 2) Existing exhaustive domain audits become binding teacher-level prerequisites.
queue=load_json('data/jlpt_teacher_review_queue.json')
queue_open=queue.get('pending', queue.get('queueCount', queue.get('count', 0)))
if isinstance(queue_open, dict): queue_open=sum(queue_open.values())
if queue_open not in (0,None): fail.append(f'vocabulary teacher review queue not empty: {queue_open}')

v5=load_json('v5-vocab-runtime-audit-status.json')
if v5.get('status')!='success': fail.append('v5 vocabulary runtime audit not successful')

gram=load_json('data/grammar_quality_v27_runtime_report.json')
if gram.get('totals',{}).get('failures')!=0 or gram.get('failures'):
    fail.append('grammar v2.7 runtime quality failures remain')
gdepth=load_json('data/grammar_depth_batch8_report.json')
if not gdepth.get('passed') or gdepth.get('failures'):
    fail.append('grammar level-depth gate failed')

listen=load_json('data/listening_completion_batch6_report.json')
if not listen.get('passed') or listen.get('eligibleRate')!=100.0:
    fail.append('listening full-catalog completion gate failed')
lfull=load_json('data/full_listening_quality_batch4_report.json')
per=lfull.get('originalCatalog',{}).get('perLevel',{})
order=['N1','N2','N3','N4','N5']
avg=[per.get(x,{}).get('avgSentenceChars',0) for x in order]
if not all(avg[i]>avg[i+1] for i in range(4)):
    fail.append(f'listening level-load progression not monotonic: {avg}')

conv=load_json('data/full_conversation_batch7_report.json')
if not conv.get('passed') or conv.get('failures'):
    fail.append('conversation full-catalog teacher quality gate failed')
cdepth=conv.get('depth',{})
cavg=[cdepth.get(x,0) for x in order]
if not all(cavg[i]>cavg[i+1] for i in range(4)):
    fail.append(f'conversation level-load progression not monotonic: {cavg}')

mockq=load_json('data/listening_mock_quality_v3_report.json')
if mockq.get('failures') or any(v.get('qualityFailures',0) for v in mockq.get('mock',{}).get('perLevel',{}).values()):
    fail.append('mock-test generated quality failures remain')

coverage=load_json('data/database_completion_report.json')
if not coverage.get('passed') or coverage.get('failures'):
    fail.append('cross-database completion gate failed')

# 3) Teacher-check the hard-coded Mock Test vocabulary fallback against the canonical teacher TSV.
audit_rows=[]
with (ROOT/'data/jlpt_teacher_audit.tsv').open(encoding='utf-8',newline='') as f:
    audit_rows=list(csv.DictReader(f,delimiter='\t'))
exact={(r.get('reading',''),r.get('display','')):r.get('level','') for r in audit_rows}
by_display={}
for r in audit_rows:
    by_display.setdefault(r.get('display',''),set()).add(r.get('level',''))

fallback_block=re.search(r'const FALLBACK_VOCAB=\{(.*?)\};\nconst FALLBACK_GRAMMAR=',mock_js,re.S)
fallback_mismatch=[]; fallback_unknown=[]; fallback_checked=0
if not fallback_block:
    fail.append('mocktest.js: FALLBACK_VOCAB block missing')
else:
    b=fallback_block.group(1)
    matches=list(re.finditer(r'N([1-5]):\[(.*?)(?=\],\nN[1-5]:|\]\s*$)',b,re.S))
    for m in matches:
        declared='N'+m.group(1)
        for word,reading,meaning in re.findall(r'\["([^"]+)","([^"]+)","([^"]*)"\]',m.group(2)):
            fallback_checked+=1
            actual=exact.get((reading,word))
            if actual and actual!=declared:
                fallback_mismatch.append({'word':word,'reading':reading,'declared':declared,'teacher':actual})
            elif not actual:
                levels=by_display.get(word,set())
                if len(levels)==1:
                    actual=next(iter(levels))
                    if actual!=declared:fallback_mismatch.append({'word':word,'reading':reading,'declared':declared,'teacher':actual})
                else:fallback_unknown.append({'word':word,'reading':reading,'declared':declared})
if fallback_mismatch:
    fail.append(f'mocktest fallback level mismatches={len(fallback_mismatch)}')

# 4) Check target vocabulary used in SPECIAL mock questions when a unique teacher level exists.
special_block=re.search(r'const SPECIAL=\{(.*?)\};\nconst QUICK_RESPONSE=',mock_js,re.S)
special_checked=[];special_mismatch=[]
if special_block:
    b=special_block.group(1)
    for lm in re.finditer(r'N([1-5]):\[(.*?)(?=\],\nN[1-5]:|\]\s*$)',b,re.S):
        declared='N'+lm.group(1)
        for term in re.findall(r'『([^』]+)』',lm.group(2)):
            levels=by_display.get(term,set())
            if len(levels)==1:
                teacher=next(iter(levels));special_checked.append({'term':term,'declared':declared,'teacher':teacher})
                if teacher!=declared:special_mismatch.append({'term':term,'declared':declared,'teacher':teacher})
if special_mismatch:
    fail.append(f'mocktest SPECIAL target level mismatches={len(special_mismatch)}')

# 5) Page-copy integrity: no page may call the project vocabulary/grammar list an official fixed JLPT list.
misleading=[]
for name in PAGES:
    s=(ROOT/name).read_text(encoding='utf-8')
    for pat in [r'官方\s*JLPT\s*(?:單字|詞彙|文法)\s*(?:清單|列表|詞表)',r'JLPT\s*官方\s*(?:單字|詞彙|文法)\s*(?:清單|列表|詞表)']:
        if re.search(pat,s,re.I): misleading.append(name)
if misleading: fail.append('misleading official fixed-list wording: '+','.join(sorted(set(misleading))))

report={
  'version':'2026-08-27-teacher-page-suitability-v1',
  'scope':'All 11 user-facing HTML pages; N1-N5 suitability is project-calibrated using teacher-audited vocabulary, established grammar/listening/conversation gates and runtime source consistency. Translator is level-neutral.',
  'pages':page_status,
  'vocabulary':{
    'teacherAuditRows':len(audit_rows),'reviewQueueOpen':queue_open or 0,'runtimeStatus':v5.get('status'),
    'mockFallbackChecked':fallback_checked,'mockFallbackMismatches':fallback_mismatch,'mockFallbackUnknown':fallback_unknown,
    'mockSpecialChecked':special_checked,'mockSpecialMismatches':special_mismatch
  },
  'grammar':{'runtimeGeneratedChecked':gram.get('totals',{}).get('webGeneratedAndChecked'),'failures':gram.get('totals',{}).get('failures'),'depthPassed':gdepth.get('passed')},
  'listening':{'catalog':lfull.get('originalCatalog',{}).get('count'),'eligibleRate':lfull.get('originalCatalog',{}).get('eligibleRate'),'avgSentenceCharsN1toN5':avg},
  'conversation':{'scenes':conv.get('sceneCount'),'dialogues':conv.get('dialogueCount'),'exactDuplicatePairs':conv.get('exactDuplicatePairs'),'avgDialogueCharsN1toN5':cavg},
  'mocktest':{'existingGeneratedQualityFailures':sum(v.get('qualityFailures',0) for v in mockq.get('mock',{}).get('perLevel',{}).values()),'teacherRuntimePrimary':"source:'teacher-runtime'" in mock_js},
  'misleadingOfficialListPages':sorted(set(misleading)),
  'failures':fail,
  'passed':not fail
}
Path('data/teacher_page_suitability_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if fail: raise SystemExit(1)
