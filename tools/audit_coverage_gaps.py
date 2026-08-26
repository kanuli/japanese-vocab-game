#!/usr/bin/env python3
from pathlib import Path
import json, re, urllib.request
from collections import Counter, defaultdict

ROOT=Path(__file__).resolve().parents[1]
LEVELS=['N5','N4','N3','N2','N1']

def norm(s): return re.sub(r'[\s　～〜・／/（）()「」『』【】\-+＋]','',str(s or '')).lower()
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def fetch_json(url):
    try:
        with urllib.request.urlopen(url,timeout=15) as r:return json.loads(r.read().decode('utf-8'))
    except Exception as e:return {'_error':str(e)}

GRAMMAR_MATRIX={
'N5':{'request':['てください'],'permission':['てもいい'],'prohibition':['てはいけない','てはいけません'],'desire':['たい'],'invitation':['ませんか'],'proposal':['ましょう'],'reason':['から'],'sequence':['てから'],'examples':['たり']},
'N4':{'experience':['たことがある'],'preparation':['ておく'],'possibility':['かもしれない'],'appearance':['そうだ','そうです'],'purpose':['ために','ように'],'condition':['なら','たら'],'concession':['ても'],'simultaneous':['ながら'],'excess':['すぎる','すぎます'],'ease':['やすい'],'difficulty':['にくい'],'change_state':['ようになる'],'potential':['可能形','potential'],'passive':['受身','受け身','passive','られる','される']},
'N3':{'decision':['ことにする'],'external_decision':['ことになる'],'rule':['ことになっている'],'habit_effort':['ようにする','ようにしています'],'change_state':['ようになる'],'every_time':['たびに'],'while_state':['うちに'],'positive_cause':['おかげで'],'negative_cause':['せいで'],'topic':['について'],'source':['によると'],'comparison':['に比べて'],'target_contrast':['に対して'],'result_discovery':['たところ'],'reasoning':['わけ'],'despite':['のに'],'occasion':['ついでに']},
'N2':{'partial_negation':['わけではない'],'impossibility':['わけがない'],'certainty':['に違いない'],'no_need':['ことはない'],'concession':['ものの','にもかかわらず'],'change_parallel':['につれて','にしたがって'],'according_to':['に応じて'],'accompanying':['に伴って'],'domain':['に関して','において'],'target_contrast':['に対して'],'unavoidable':['ざるを得ない'],'risk':['かねない'],'polite_impossible':['かねる'],'basis':['ことから'],'limit':['限り'],'after_considering':['上で'],'not_only':['ばかりか'],'far_from':['どころか'],'not_always':['とは限らない']},
'N1':{'let_alone':['はおろか'],'not_limited':['にとどまらず'],'starting_with':['を皮切りに'],'as_of_by':['をもって'],'in_line_with':['に即して'],'inevitable_effect':['ずにはおかない'],'no_need':['までもない'],'extreme':['極まりない'],'cannot_suppress':['禁じ得ない'],'up_to':['に至るまで'],'if_special_case':['とあれば'],'as_soon_as':['が早いか'],'again_and_again':['そばから'],'without':['なくしては'],'forced':['余儀なくされる'],'unbearable_worthy':['に堪えない'],'not_even_one':['たりとも'],'must_not':['べからず'],'almost_as_if':['んばかり'],'while_also':['かたわら']}}

JF_TOPICS={
'self_family':['家族','自己紹介','名前','結婚','子育て','家庭'],'housing':['部屋','住宅','不動産','引っ越','水道','電気','ガス','ごみ','近所','住まい'],'leisure':['映画','音楽','スポーツ','趣味','イベント','コンサート','娯楽','劇場'],'life_lifecycle':['生活','日課','役所','行政','手続','冠婚葬祭','暮らし'],'work':['仕事','会社','職場','会議','商務','報告','顧客','上司','勤務'],'travel_transport':['旅行','駅','電車','バス','空港','飛行機','船','フェリー','タクシー','交通','観光'],'health':['病院','薬','健康','診察','医療','歯科','クリニック'],'shopping':['買い物','返品','交換','支払','店','商品','スーパー','コンビニ'],'food':['レストラン','注文','料理','食事','カフェ','飲食','食べ物','アレルギー','材料','餐廳','咖啡'],'nature_environment':['天気','災害','避難','自然','環境','台風','地震','大雨','防災','天氣','アウトドア','登山'],'relationships':['友達','人間関係','謝罪','相談','トラブル','近所','交際'],'education':['学校','大学','授業','勉強','図書館','教育','教室','学習'],'language_culture':['日本語','文化','神社','寺','祭り','言語','マナー','伝統','語言','文化'],'society':['警察','社会','銀行','保険','入管','法律','行政','市役所'],'science_technology':['技術','スマホ','インターネット','アカウント','パソコン','オンライン','システム']}
FUNCTIONS={'request':['ください','お願いします','いただけます'],'permission':['てもいい','可能ですか','よろしいですか'],'apology':['すみません','申し訳'],'refusal':['できません','難しい','お断り','いたしかね'],'clarification':['確認したい','ということですか','もう一度','聞き逃'],'change_reschedule':['変更','取り直','改めて','別の時間','振り替'],'complaint_problem':['困って','問題','故障','届いていない','違う','不具合'],'negotiation_alternative':['別の方法','代わり','調整','対応していただく','ほかの方法','別の案'],'procedure':['手続','必要書類','受付','申請','提出'],'reporting':['報告','連絡','共有','伝えて'],'emergency':['緊急','避難','事故','警察','救急','災害'],'reason_explanation':['ので','ため','理由','事情','から'],'exception':['例外','通常の方法以外','事情がある場合','今回に限り'],'recommendation':['ほうがいい','おすすめ','ましょう','したほう'],'comparison':['比べ','より','一方','ほうが']}
FUNCTION_EXPECTED={'N5':['request','permission','apology','clarification'],'N4':['request','permission','apology','clarification','change_reschedule','reason_explanation','recommendation'],'N3':['request','apology','clarification','change_reschedule','complaint_problem','procedure','reporting','reason_explanation','recommendation','comparison'],'N2':['request','apology','refusal','clarification','change_reschedule','complaint_problem','negotiation_alternative','procedure','reporting','reason_explanation','exception','recommendation','comparison'],'N1':['request','apology','refusal','clarification','change_reschedule','complaint_problem','negotiation_alternative','procedure','reporting','reason_explanation','exception','comparison']}

def collect_grammar():
    per=defaultdict(list);remote={}
    s=read('grammar.html')
    for level,gram in re.findall(r'"level":"(N[1-5])"[^{}]{0,450}?"grammar":"([^"]+)"',s):per[level].append(gram)
    for f in ['grammar-reference-expansion.js','grammar-gap-expansion.js']:
        x=read(f)
        for level,gram in re.findall(r"add\('(N[1-5])','([^']+)'",x):per[level].append(gram)
        if f=='grammar-gap-expansion.js':
            for gram in re.findall(r"add\('[^']*',\[[^\]]+\],'[^']*','([^']+)'",x):per['N4'].append(gram)
    base='https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/'
    for level in LEVELS:
        d=fetch_json(base+f'grammar_ja_{level}_full_alphabetical_0001.json')
        if isinstance(d,list):per[level]+=[str(x.get('title','')) for x in d];remote[level]=len(d)
        else:remote[level]=d.get('_error','unknown')
    return per,remote

def grammar_audit():
    per,remote=collect_grammar();out={}
    for level in LEVELS:
        hay=norm(' | '.join(per[level]));covered=[];missing=[]
        for fn,aliases in GRAMMAR_MATRIX[level].items():(covered if any(norm(a) in hay for a in aliases) else missing).append(fn)
        out[level]={'signals':len(per[level]),'covered':covered,'missing':missing,'coveragePct':round(100*len(covered)/len(GRAMMAR_MATRIX[level]),1)}
    return out,remote

def parse_reference_listening():
    s=read('listening-reference-expansion.js');rows=[]
    for level in LEVELS:
        m=re.search(rf'\b{level}:\[(.*?)(?=\n\],\nN[1-5]:|\n\]\n\}};)',s,re.S)
        if m:
            for jp,zh,t in re.findall(r"\['([^']*)','([^']*)','([^']*)'\]",m.group(1)):rows.append({'level':level,'typeZh':t,'jp':jp})
    return rows

def parse_gap_listening_types():
    s=read('listening-gap-expansion.js');rows=[]
    block=re.search(r'const types=\{(.*?)\};\nconst f=',s,re.S)
    if not block:return rows
    for level in LEVELS:
        m=re.search(rf'{level}:\[([^\]]+)\]',block.group(1))
        if not m:continue
        ts=re.findall(r"'([^']+)'",m.group(1))
        for i in range(44):rows.append({'level':level,'typeZh':ts[i%len(ts)],'jp':f'generated-gap-{i}'})
    return rows

def listening_audit():
    d=json.loads(read('listening-original-catalog.json'));rows=[x for x in d.get('items',[]) if x.get('level') in LEVELS]+parse_reference_listening()+parse_gap_listening_types();out={}
    for level in LEVELS:
        r=[x for x in rows if x.get('level')==level];tc=Counter(str(x.get('typeZh') or x.get('type') or '未分類') for x in r)
        out[level]={'count':len(r),'distinctTypes':len(tc),'topTypes':tc.most_common(20),'underrepresented':sorted([[k,v] for k,v in tc.items() if v<5],key=lambda x:(x[1],x[0]))}
    return out

def conversation_audit():
    files=[f'conversation-data-{i}.js' for i in range(1,6)]+['conversation-expansion.js','conversation-world-expansion.js','conversation-reference-expansion.js','conversation-gap-expansion.js']
    text='\n'.join(read(f) for f in files if (ROOT/f).exists());scenes=[]
    patterns=[r'\{"id":"([^"]+)","icon":"[^"]*","zh":"([^"]+)","jp":"([^"]+)"',r"S\('([^']+)'\s*,\s*'[^']*'\s*,\s*'([^']+)'\s*,\s*'([^']+)'",r"addScene\(\{id:'([^']+)',icon:'[^']*',zh:'([^']+)',jp:'([^']+)'",r"id:\s*'([^']+)'.{0,150}?zh:\s*'([^']+)'.{0,150}?jp:\s*'([^']+)'" ]
    for pat in patterns:
        for m in re.finditer(pat,text,re.S):
            if not any(x['id']==m.group(1) for x in scenes):scenes.append({'id':m.group(1),'zh':m.group(2),'jp':m.group(3)})
    topic_counts=Counter();scene_topics={}
    for sc in scenes:
        hay=norm(sc['zh']+' '+sc['jp']+' '+sc['id']);hits=[]
        for topic,kws in JF_TOPICS.items():
            if any(norm(k) in hay for k in kws):hits.append(topic);topic_counts[topic]+=1
        scene_topics[sc['id']]=hits
    level_functions={}
    for level in LEVELS:
        json_snips=re.findall(rf'\{{"level":"{level}".*?"lines":\[.*?\]\}}',text,re.S);gen_snips=re.findall(rf"item\('{level}'.{{0,1300}}?\)\s*[,;]",text,re.S);local=' '.join(json_snips+gen_snips)
        counts={fn:sum(local.count(k) for k in kws) for fn,kws in FUNCTIONS.items()};weak=[fn for fn in FUNCTION_EXPECTED[level] if counts.get(fn,0)<1]
        level_functions[level]={'signalCounts':counts,'weakExpected':weak}
    return {'sceneCount':len(scenes),'topicCounts':dict(topic_counts),'weakTopics':[t for t in JF_TOPICS if topic_counts[t]<2],'levelFunctions':level_functions,'sceneTopics':scene_topics}

def main():
    grammar,remote=grammar_audit();listening=listening_audit();conversation=conversation_audit();report={'version':'2026-08-27-gap-audit-v3','methodology':{'jlpt':'Official JLPT capability descriptions are the difficulty anchor; grammar matrix is diagnostic, not an official syllabus.','jfStandard':'Conversation topic coverage uses the Japan Foundation JF Standard 15-topic framework as a diagnostic taxonomy.','copyright':'External proprietary sites are reference-only and are not scraped or copied.'},'grammar':grammar,'hanabiraRemoteStatus':remote,'listening':listening,'conversation':conversation}
    p=ROOT/'data/coverage_gap_audit.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(p.relative_to(ROOT)),'grammarMissing':{k:v['missing'] for k,v in grammar.items()},'listeningUnderrepresented':{k:v['underrepresented'] for k,v in listening.items()},'weakTopics':conversation['weakTopics'],'weakFunctions':{k:v['weakExpected'] for k,v in conversation['levelFunctions'].items()}},ensure_ascii=False))
if __name__=='__main__':main()
