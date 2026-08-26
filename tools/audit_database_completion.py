#!/usr/bin/env python3
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/'data'/name).read_text(encoding='utf-8'))
ref=load('reference_expansion_quality_report.json')
cov=load('coverage_gap_audit.json')
q3=load('quality_depth_batch3_report.json')
l4=load('full_listening_quality_batch4_report.json')
l6=load('listening_completion_batch6_report.json')
c7=load('full_conversation_batch7_report.json')
g8=load('grammar_depth_batch8_report.json')
fail=[]
if not ref.get('passed'):fail.append('reference expansion QA failed')
if ref.get('grammar',{}).get('count')!=108:fail.append('grammar reference count !=108')
if ref.get('listening',{}).get('count')!=273:fail.append('unique listening reference expansion count !=273')
for lv,x in cov.get('grammar',{}).items():
    if x.get('missing'):fail.append(f'{lv} grammar coverage missing={x.get("missing")}')
for lv,x in cov.get('listening',{}).items():
    if x.get('underrepresented'):fail.append(f'{lv} listening underrepresented={x.get("underrepresented")}')
conv=cov.get('conversation',{})
if conv.get('weakTopics'):fail.append(f'conversation weakTopics={conv.get("weakTopics")}')
for lv,x in conv.get('levelFunctions',{}).items():
    if x.get('weakExpected'):fail.append(f'{lv} weakExpected={x.get("weakExpected")}')
if not q3.get('passed'):fail.append('Batch 3 quality-depth QA failed')
if not l4.get('passed'):fail.append('full listening Batch 4 QA failed')
if not l6.get('passed'):fail.append('full listening completion Batch 6 failed')
if l6.get('catalogCount')!=6690 or l6.get('qualityEligible')!=6690 or l6.get('eligibleRate')!=100.0:fail.append('listening catalog is not 6690/6690 quality eligible')
if l6.get('qualityFailures'):fail.append(f'listening quality failures={l6.get("qualityFailures")}')
if not c7.get('passed'):fail.append('full conversation Batch 7 QA failed')
if c7.get('sceneCount')!=77 or c7.get('dialogueCount')!=1925:fail.append('conversation count is not 77 scenes / 1925 dialogues')
if c7.get('structureErrors') or c7.get('kanaZhCount') or c7.get('exactDuplicatePairs') or c7.get('awkwardGenericProgressionTemplates'):fail.append('conversation structural/language/duplicate/template failures remain')
if not g8.get('passed'):fail.append('grammar depth Batch 8 QA failed')
for lv,x in g8.get('byLevel',{}).items():
    if x.get('structuralErrors'):fail.append(f'{lv} grammar structuralErrors={x.get("structuralErrors")}')
page=ref.get('pageChecks',{})
for k in ('grammar','listening','conversation','mocktest'):
    if page.get(k) is not True:fail.append(f'page check failed: {k}')
report={
 'version':'2026-08-27-japanese-database-completion-v1',
 'scope':'Current project reference/diagnostic grammar, listening and conversation databases plus page integration gates.',
 'status':{
  'grammar':{'referenceQuestions':ref.get('grammar',{}).get('count'),'coverageMissing':sum(len(x.get('missing',[])) for x in cov.get('grammar',{}).values()),'depthGatePassed':g8.get('passed')},
  'listening':{'originalCatalog':l6.get('catalogCount'),'qualityEligible':l6.get('qualityEligible'),'eligibleRate':l6.get('eligibleRate'),'referenceExpansionUnique':ref.get('listening',{}).get('count'),'underrepresentedSubtypes':sum(len(x.get('underrepresented',[])) for x in cov.get('listening',{}).values())},
  'conversation':{'scenes':c7.get('sceneCount'),'dialogues':c7.get('dialogueCount'),'weakTopics':len(conv.get('weakTopics',[])),'weakExpectedFunctions':sum(len(x.get('weakExpected',[])) for x in conv.get('levelFunctions',{}).values()),'exactDuplicatePairs':c7.get('exactDuplicatePairs'),'awkwardGenericTemplates':c7.get('awkwardGenericProgressionTemplates')},
  'pageChecks':page
 },
 'interpretation':'Completed means all current project-defined coverage, structural, quality-depth, duplication, language-leakage and integration hard gates pass. It does not mean an official JLPT syllabus is exhausted, because JLPT publishes capability descriptions rather than a fixed official grammar/vocabulary list.',
 'failures':fail,'passed':not fail
}
(ROOT/'data'/'database_completion_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if fail:raise SystemExit('Cross-database completion gate failed')
