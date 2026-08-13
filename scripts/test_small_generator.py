#!/usr/bin/env python3
from pathlib import Path
import json
from listening_jlpt_style_core import *
OUT=Path('listening-original-catalog.json')

def item(level,typ,i):
    name,time,day,place,alt,obj,event,reason=combo(i,NAMES,TIMES,DAYS,PLACES,ALT_PLACES,OBJECTS,EVENTS,REASONS)
    if typ=='quick_response':
        if level=='N5': jp=f'{name}、{day}の{event}は{time}からです。遅れないでください。';c=f'{day}的{event}是{time}開始，要準時到。';ds=[f'{day}的{event}是十一時開始，要準時到。',f'今天的{event}是{time}開始。',f'{day}的{event}是{time}結束。']
        elif level=='N4': jp=f'{name}、{day}の{event}は十時ではなく、{time}からに変わりました。';c=f'{day}的{event}改為{time}開始。';ds=[f'{day}的{event}仍是十時開始。',f'今天的{event}改為{time}開始。',f'{day}的{event}改為{time}結束。']
        elif level=='N3': jp=f'{day}の{event}は{time}開始です。ただし、受付は三十分前までに済ませてください。';c=f'{event}{time}開始，但要提前三十分鐘完成報到。';ds=[f'{event}{time}開始，開始後三十分鐘才報到。','活動改到十一時開始，而且不用提早報到。',f'{event}{time}結束前三十分鐘才報到。']
        elif level=='N2': jp=f'{day}の{event}は予定どおり{time}開始ですが、資料配布の都合で参加者は二十分前には会場に入ってください。';c=f'活動仍在{time}開始，但參加者要提前二十分鐘進場。';ds=['活動延後開始，所以不用提早進場。',f'活動在{time}結束，參加者要提早離場。',f'活動在{time}開始，但只有工作人員要提早進場。']
        else: jp=f'{day}の{event}自体は{time}開始で変更ありません。ただ、混雑を避けるため受付は開始二十五分前を目安に締め切るとのことです。';c=f'活動仍在{time}開始，但報到約在開始前二十五分鐘截止。';ds=['活動提前二十五分鐘開始。',f'活動在{time}開始，報到在開始後二十五分鐘截止。','活動時間未變，而且報到直到開始後都可辦理。']
    elif typ=='point':
        if level in ('N5','N4'): jp=f'女の人：{time}に{place}で会いましょう。男の人：{alt}ではなく、{place}ですね。女の人：はい。二人はどこで会いますか。';c=f'在{place}見面。';ds=[f'在{alt}見面。',f'在{place}附近的入口見面。',f'先到{alt}再去{place}。']
        elif level=='N3': jp=f'女の人：{time}に{place}で会う予定でしたが、私は少し遅れそうです。男の人：では、私は先に{place}へ行って待っています。男の人はどうしますか。';c=f'先去{place}等對方。';ds=[f'改去{alt}等對方。',f'等對方到了才去{place}。','取消見面。']
        elif level=='N2': jp=f'女の人：{time}に{place}で待ち合わせでしたよね。男の人：駅前は工事中なので、{place}の東側の入口にしましょう。女の人はどこへ行けばいいですか。';c=f'去{place}的東側入口。';ds=[f'去{place}的西側入口。','去車站前的施工入口。',f'去{alt}的東側入口。']
        else: jp=f'女の人：{time}に{place}という話でしたが、正面入口は工事で閉鎖中だそうです。男の人：では、建物を回って東側の職員入口の前にしましょう。最終的な待ち合わせ場所はどこですか。';c=f'在{place}東側的職員入口前。';ds=[f'在{place}正面入口前。',f'在{place}西側職員入口前。',f'在{alt}東側入口前。']
    elif typ=='task':
        a,b,d=combo(i,CHORES,CHORES,CHORES)
        if len({a,b,d})<3:d=CHORES[(CHORES.index(a)+3)%len(CHORES)];b=CHORES[(CHORES.index(a)+1)%len(CHORES)]
        if level=='N5': jp=f'先生：まず、{a}。それから、{b}。最初に何をしますか。';c=a;ds=[b,d,f'{b}の後で{a}']
        elif level=='N4': jp=f'上司：最初に{a}。終わったら{b}。時間があれば{d}。まず何をしますか。';c=a;ds=[b,d,'三件事同時開始。']
        elif level=='N3': jp=f'上司：{reason}ので予定を変えます。まず{a}。その後で{b}。{d}は午後でかまいません。最初にすることは何ですか。';c=a;ds=[b,d,'完全按原定順序。']
        elif level=='N2': jp=f'上司：本来は{b}からですが、{reason}ので順番を入れ替えます。先に{a}を済ませ、その結果を確認してから{b}へ進んでください。最初の作業は何ですか。';c=a;ds=[b,d,f'{a}和{b}同時進行。']
        else: jp=f'上司：通常なら{b}を先にしますが、今日は{reason}ため例外です。{a}を優先し、問題がなければ{b}へ進んでください。{d}は最後で構いません。最優先は何ですか。';c=a;ds=[b,d,f'照常先做{b}。']
    elif typ=='summary':
        if level=='N5': jp=f'{day}の{event}は、{reason}ので中止です。次は金曜日です。何が決まりましたか。';c=f'{day}的{event}取消，改到星期五。';ds=[f'星期五的{event}取消，改到{day}。',f'{day}照常舉行。','只改地點，不改日期。']
        elif level=='N4': jp=f'{day}の{event}は、{reason}ため、{place}では行いません。日付は変えず、会場だけ{alt}に変更します。大切な変更は何ですか。';c=f'日期不變，只把會場改到{alt}。';ds=['會場不變，只改日期。','日期和會場都改了。','活動完全取消。']
        elif level=='N3': jp=f'{event}についてお知らせします。{reason}ため、開始時刻は変えませんが、会場を{place}から{alt}へ変更します。要点は何ですか。';c=f'開始時間不變，但會場由{place}改到{alt}。';ds=['會場不變，但開始時間延後。','活動取消。',f'會場改到{alt}，開始時間也提早。']
        elif level=='N2': jp=f'{event}は予定どおり{day}に実施します。ただし、{reason}影響で{place}が使えないため会場のみ{alt}へ移します。開始時刻に変更はありません。最も重要な内容は何ですか。';c='日期和開始時間不變，只更換會場。';ds=['日期延後，但會場不變。','活動取消。','會場和開始時間都改了。']
        else: jp=f'{event}は延期案も出ましたが、最終的には{day}の予定を維持します。{reason}ため{place}は使えず、会場だけ{alt}へ移します。開始時刻も変更ありません。結論は何ですか。';c='按原日期和時間舉行，只更換會場。';ds=['延期到其他日期，會場不變。','日期不變，但開始時間和會場都改了。','活動取消。']
    else:
        if level=='N5': jp=f'女の人：{obj}を忘れました。男の人：{place}にありますよ。女の人：じゃ、取りに行きます。女の人は何をしますか。';c=f'去{place}拿回{obj}。';ds=[f'把{obj}帶去{place}。',f'在{place}買新的{obj}。',f'把{obj}丟掉。']
        elif level=='N4': jp=f'男の人：{obj}はもう確認しましたか。女の人：まだです。先に{place}へ行くので、そのあとにします。女の人はまず何をしますか。';c=f'先去{place}。';ds=[f'先處理{obj}。','叫男方先去。','取消外出。']
        elif level=='N3': jp=f'女の人：{obj}を今日中に確認するつもりでしたが、{reason}そうです。男の人：明日の朝でも大丈夫ですよ。女の人：そうします。どうすることにしましたか。';c=f'把處理{obj}改到明早。';ds=[f'今天一定處理{obj}。',f'不再處理{obj}。','交給別人後不再確認。']
        elif level=='N2': jp=f'女の人：{obj}を今日中に確認する必要がありますが、{reason}と聞きました。男の人：急ぎでなければ明日に回せます。女の人：締め切りは明日の昼なので朝一番にします。意図は何ですか。';c=f'今天不勉強處理，改在明早優先處理{obj}。';ds=[f'完全放棄處理{obj}。',f'今天一定處理{obj}。','全部交給男方。']
        else: jp=f'女の人：{obj}は本日中に確認予定でしたが、{reason}とのことです。男の人：期限に余裕があるなら状況が落ち着いてからでもいいのでは。女の人：締め切りは明日の正午ですから、朝一番で確実に対応します。重視していることは何ですか。';c='不勉強今天完成，而是在期限前的明早確實處理。';ds=['即使出問題也必須今天完成。','把期限延到後天。','完全交給別人不再確認。']
    return {'jp':jp,'choices':rotate(c,ds,i),'correct':c}

def main():
    base=base_counts();items=[];types=list(TYPE_LABELS)
    for level in LEVELS:
        need=TARGET_PER_LEVEL-base[level];assert need>=0
        for n in range(need):
            typ=types[n%len(types)];q=item(level,typ,n//len(types)+LEVELS.index(level)*10000)
            items.append({'id':f'JL-{level}-{n+1:04d}','level':level,'type':typ,'typeZh':TYPE_LABELS[typ],'jp':q['jp'],'choicesZh':q['choices'],'correctZh':q['correct'],'explanationZh':f'{TYPE_LABELS[typ]}：答案只取決於錄音中的關鍵時間、地點、順序、結論或意圖。正確答案：{q["correct"]}','structured':True,'source':'原創 JLPT 風格練習'})
    assert len({x['id'] for x in items})==len(items)
    combined={l:base[l]+sum(x['level']==l for x in items) for l in LEVELS};assert set(combined.values())=={TARGET_PER_LEVEL}
    doc={'version':1,'copyright':'Original practice content; not copied from official JLPT questions.','targetPerLevel':TARGET_PER_LEVEL,'baseCounts':base,'combinedCounts':combined,'baseTotal':sum(base.values()),'originalTotal':len(items),'combinedTotal':sum(combined.values()),'typeLabels':TYPE_LABELS,'items':items}
    OUT.write_text(json.dumps(doc,ensure_ascii=False,separators=(',',':')),encoding='utf-8');print('EXACT',combined,'TOTAL',doc['combinedTotal'],'ORIGINAL',len(items))
if __name__=='__main__':main()
