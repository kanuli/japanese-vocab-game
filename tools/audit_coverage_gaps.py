#!/usr/bin/env python3
from pathlib import Path
import json, re, urllib.request
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
LEVELS = ['N5','N4','N3','N2','N1']

def norm(s):
    return re.sub(r'[\s　～〜・／/（）()「」『』【】\-]', '', str(s or '')).lower()

def read(p): return (ROOT / p).read_text(encoding='utf-8')

def fetch_json(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'_error': str(e)}

# Representative grammar functions, not an official JLPT syllabus.
GRAMMAR_MATRIX = {
'N5': {
 'request':['てください'], 'permission':['てもいい'], 'prohibition':['てはいけない'],
 'desire':['たい'], 'invitation':['ませんか'], 'proposal':['ましょう'],
 'reason':['から'], 'sequence':['てから'], 'examples':['たり'], 'basic_condition':['たら']},
'N4': {
 'experience':['たことがある'], 'preparation':['ておく'], 'possibility':['かもしれない'],
 'appearance':['そうだ','そうです'], 'purpose':['ために','ように'], 'condition':['なら','たら'],
 'concession':['ても'], 'simultaneous':['ながら'], 'excess':['すぎる','すぎます'],
 'ease':['やすい'], 'difficulty':['にくい'], 'change_state':['ようになる'],
 'potential':['可能形'], 'passive':['受身']},
'N3': {
 'decision':['ことにする'], 'external_decision':['ことになる'], 'rule':['ことになっている'],
 'habit_effort':['ようにする'], 'change_state':['ようになる'], 'every_time':['たびに'],
 'while_state':['うちに'], 'positive_cause':['おかげで'], 'negative_cause':['せいで'],
 'topic':['について'], 'source':['によると'], 'comparison':['に比べて'],
 'target_contrast':['に対して'], 'result_discovery':['たところ'], 'reasoning':['わけ'],
 'despite':['のに'], 'occasion':['ついでに']},
'N2': {
 'partial_negation':['わけではない'], 'impossibility':['わけがない'], 'certainty':['に違いない'],
 'no_need':['ことはない'], 'concession':['ものの','にもかかわらず'], 'change_parallel':['につれて','にしたがって'],
 'according_to':['に応じて'], 'accompanying':['に伴って'], 'domain':['に関して','において'],
 'target_contrast':['に対して'], 'unavoidable':['ざるを得ない'], 'risk':['かねない'],
 'polite_impossible':['かねる'], 'basis':['ことから'], 'limit':['限り'], 'after_considering':['上で'],
 'not_only':['ばかりか'], 'far_from':['どころか'], 'not_always':['とは限らない']},
'N1': {
 'let_alone':['はおろか'], 'not_limited':['にとどまらず'], 'starting_with':['を皮切りに'],
 'as_of_by':['をもって'], 'in_line_with':['に即して'], 'inevitable_effect':['ずにはおかない'],
 'no_need':['までもない'], 'extreme':['極まりない'], 'cannot_suppress':['禁じ得ない'],
 'up_to':['に至るまで'], 'if_special_case':['とあれば'], 'as_soon_as':['が早いか'],
 'again_and_again':['そばから'], 'without':['なくしては'], 'forced':['余儀なくされる'],
 'unbearable_worthy':['に堪えない'], 'not_even_one':['たりとも'], 'must_not':['べからず'],
 'almost_as_if':['んばかり'], 'while_also':['かたわら']}
}

# JF Standard 15 topics; keyword mapping is only for coverage diagnostics.
JF_TOPICS = {
 'self_family':['家族','自己紹介','名前','結婚','子育て'],
 'housing':['部屋','住宅','不動産','引っ越','水道','電気','ガス','ごみ','近所'],
 'leisure':['映画','音楽','スポーツ','趣味','イベント','コンサート','娯楽'],
 'life_lifecycle':['生活','日課','役所','行政','手続','冠婚葬祭'],
 'work':['仕事','会社','職場','会議','商務','報告','顧客','上司'],
 'travel_transport':['旅行','駅','電車','バス','空港','飛行機','船','フェリー','タクシー','交通'],
 'health':['病院','薬','健康','診察','医療','歯科'],
 'shopping':['買い物','返品','交換','支払','店','商品'],
 'food':['レストラン','注文','料理','食事','カフェ','飲食'],
 'nature_environment':['天気','災害','避難','自然','環境','台風','地震'],
 'relationships':['友達','人間関係','謝罪','相談','トラブル','近所'],
 'education':['学校','大学','授業','勉強','図書館','教育'],
 'language_culture':['日本語','文化','神社','寺','祭り','言語'],
 'society':['警察','社会','銀行','保険','入管','法律','行政'],
 'science_technology':['技術','スマホ','インターネット','アカウント','パソコン','オンライン']
}

FUNCTIONS = {
 'request':['ください','お願いします','いただけます'],
 'permission':['てもいい','可能ですか'],
 'apology':['すみません','申し訳'],
 'refusal':['できません','難しい','お断り'],
 'clarification':['確認したい','ということですか','もう一度'],
 'change_reschedule':['変更','取り直','改めて','別の時間'],
 'complaint_problem':['困って','問題','故障','届いていない','違う'],
 'negotiation_alternative':['別の方法','代わり','調整','対応していただく'],
 'procedure':['手続','必要書類','受付','申請'],
 'reporting':['報告','連絡','共有'],
 'emergency':['緊急','避難','事故','警察','救急'],
 'reason_explanation':['ので','ため','理由','事情'],
 'exception':['例外','通常の方法以外','事情がある場合'],
 'recommendation':['ほうがいい','おすすめ','ましょう'],
 'comparison':['比べ','より','一方']
}

def collect_grammar():
    per = defaultdict(list)
    # Built-in + already-integrated original questions in grammar.html.
    s = read('grammar.html')
    for level, gram in re.findall(r'"level":"(N[1-5])"[^{}]{0,450}?"grammar":"([^"]+)"', s):
        per[level].append(gram)
    # Expansion add(level, grammar, ...)
    e = read('grammar-reference-expansion.js')
    for level, gram in re.findall(r"add\('(N[1-5])','([^']+)'", e):
        per[level].append(gram)
    # Hanabira titles already used by the runtime.
    remote_status = {}
    base='https://raw.githubusercontent.com/tristcoil/hanabira.org-japanese-content/main/grammar_json/'
    for level in LEVELS:
        d = fetch_json(base+f'grammar_ja_{level}_full_alphabetical_0001.json')
        if isinstance(d, list):
            per[level] += [str(x.get('title','')) for x in d]
            remote_status[level] = len(d)
        else:
            remote_status[level] = d.get('_error','unknown')
    return per, remote_status

def grammar_audit():
    per, remote = collect_grammar()
    out={}
    for level in LEVELS:
        hay=norm(' | '.join(per[level]))
        covered=[]; missing=[]
        for fn, aliases in GRAMMAR_MATRIX[level].items():
            ok=any(norm(a) in hay for a in aliases)
            (covered if ok else missing).append(fn)
        out[level]={'signals':len(per[level]),'covered':covered,'missing':missing,'coveragePct':round(100*len(covered)/len(GRAMMAR_MATRIX[level]),1)}
    return out,remote

def parse_reference_listening():
    s=read('listening-reference-expansion.js')
    rows=[]
    for m in re.finditer(r"level:'(N[1-5])'.{0,500}?typeZh:'([^']+)'.{0,900}?jp:'([^']+)'",s,re.S):
        rows.append({'level':m.group(1),'typeZh':m.group(2),'jp':m.group(3)})
    return rows

def listening_audit():
    d=json.loads(read('listening-original-catalog.json'))
    rows=[x for x in d.get('items',[]) if x.get('level') in LEVELS]
    rows += parse_reference_listening()
    out={}
    for level in LEVELS:
        r=[x for x in rows if x.get('level')==level]
        tc=Counter(str(x.get('typeZh') or x.get('type') or '未分類') for x in r)
        out[level]={'count':len(r),'distinctTypes':len(tc),'topTypes':tc.most_common(12),'underrepresented':[k for k,v in tc.items() if v<8]}
    return out

def conversation_audit():
    files=[f'conversation-data-{i}.js' for i in range(1,6)]+['conversation-expansion.js','conversation-world-expansion.js','conversation-reference-expansion.js']
    text='\n'.join(read(f) for f in files if (ROOT/f).exists())
    scenes=[]
    # S('id','icon','zh','jp',...)
    for m in re.finditer(r"S\('([^']+)'\s*,\s*'[^']*'\s*,\s*'([^']+)'\s*,\s*'([^']+)'",text):
        scenes.append({'id':m.group(1),'zh':m.group(2),'jp':m.group(3)})
    # Older direct root.push specs if present.
    for m in re.finditer(r"id:\s*'([^']+)'.{0,150}?zh:\s*'([^']+)'.{0,150}?jp:\s*'([^']+)'",text,re.S):
        if not any(x['id']==m.group(1) for x in scenes): scenes.append({'id':m.group(1),'zh':m.group(2),'jp':m.group(3)})
    topic_counts=Counter(); scene_topics={}
    for sc in scenes:
        hay=norm(sc['zh']+' '+sc['jp']+' '+sc['id'])
        hits=[]
        for topic, kws in JF_TOPICS.items():
            if any(norm(k) in hay for k in kws): hits.append(topic);topic_counts[topic]+=1
        scene_topics[sc['id']]=hits
    level_function=defaultdict(Counter)
    # Count communicative-function signals by N-level across dialogue text.
    for level in LEVELS:
        for fn,kws in FUNCTIONS.items():
            count=0
            for kw in kws:
                count += len(re.findall(re.escape(kw), text)) if level not in text else 0
            # Better level-local snippets around item('Nx', ...)
            snippets=re.findall(rf"item\('{level}'.{{0,650}}?\)\s*[,;]",text,re.S)
            local=' '.join(snippets)
            level_function[level][fn]=sum(local.count(k) for k in kws)
    weak_topics=[t for t in JF_TOPICS if topic_counts[t]<2]
    weak_functions={l:[f for f,c in level_function[l].items() if c<2] for l in LEVELS}
    return {'sceneCount':len(scenes),'topicCounts':dict(topic_counts),'weakTopics':weak_topics,'weakFunctions':weak_functions,'sceneTopics':scene_topics}

def main():
    grammar,remote=grammar_audit()
    listening=listening_audit()
    conversation=conversation_audit()
    report={
      'version':'2026-08-27-gap-audit-v1',
      'methodology':{
        'jlpt':'Official JLPT capability descriptions are the difficulty anchor; grammar matrix is diagnostic, not an official syllabus.',
        'jfStandard':'Conversation topic coverage uses the Japan Foundation JF Standard 15-topic framework as a diagnostic taxonomy.',
        'copyright':'External proprietary sites are reference-only and are not scraped or copied.'
      },
      'grammar':grammar,'hanabiraRemoteStatus':remote,'listening':listening,'conversation':conversation
    }
    p=ROOT/'data/coverage_gap_audit.json';p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'report':str(p.relative_to(ROOT)),'grammarMissing':{k:v['missing'] for k,v in grammar.items()},'weakTopics':conversation['weakTopics'],'weakFunctions':conversation['weakFunctions']},ensure_ascii=False))

if __name__=='__main__': main()
