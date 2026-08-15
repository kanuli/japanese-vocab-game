#!/usr/bin/env python3
from pathlib import Path

p=Path('.github/workflows/generate-conversation-voicevox-43.yml')
s=p.read_text(encoding='utf-8')
s=s.replace("assert d['conversationCount']==650 and d['sourceLineCount']==1300 and d['utteranceCount']==1244", "assert d['sceneCount']==61 and d['conversationCount']==1525 and d['sourceLineCount']==3050 and d['utteranceCount']>=2600")
s=s.replace("43 VOICEVOX canonical speakers covering all 1,244 unique utterances in 650 situation conversations.", "43 VOICEVOX canonical speakers covering the complete expanded 61-scene / 1,525-conversation catalog.")
s=s.replace("assert m['count']==1244 and len(m['members'])==1244", "cat=json.load(open('conversation-audio-catalog.json')); expected=cat['utteranceCount']; assert m['count']==expected and len(m['members'])==expected")
s=s.replace("assert d['status']=='ready' and d['speakerCount']==43 and d['utteranceCount']==1244 and d['recordingCount']==53492", "assert d['status']=='ready' and d['sceneCount']==61 and d['conversationCount']==1525 and d['sourceLineCount']==3050 and d['speakerCount']==43 and d['utteranceCount']>=2600 and d['recordingCount']==43*d['utteranceCount']")
p.write_text(s,encoding='utf-8')

p=Path('.github/workflows/generate-conversation-supertonic.yml')
s=p.read_text(encoding='utf-8')
s=s.replace('Build exact 650-conversation utterance catalog','Build exact 1525-conversation utterance catalog')
s=s.replace("if(d.sceneCount!==26||d.conversationCount!==650)throw new Error('Expected 26 scenes / 650 conversations');", "if(d.sceneCount!==61||d.conversationCount!==1525)throw new Error('Expected 61 scenes / 1525 conversations');")
s=s.replace("if(d.sourceLineCount!==1300)throw new Error('Expected 1,300 source lines');", "if(d.sourceLineCount!==3050)throw new Error('Expected 3,050 source lines');")
s=s.replace("if(d.utteranceCount!==1244)throw new Error('Expected 1,244 unique utterances');", "if(d.utteranceCount<2600)throw new Error('Expected at least 2,600 unique utterances');")
s=s.replace("covering all 1,244 unique utterances from 650 conversations.", "covering the complete expanded 61-scene / 1,525-conversation catalog.")
s=s.replace("assert m['voice']==v and m['count']==1244", "cat=json.load(open('conversation-audio-catalog.json')); expected=cat['utteranceCount']; assert m['voice']==v and m['count']==expected")
s=s.replace("assert len(files)==1244==len(m['members'])", "assert len(files)==expected==len(m['members'])")
s=s.replace("assert d['conversationCount']==650 and d['sourceLineCount']==1300 and d['utteranceCount']==1244", "assert d['sceneCount']==61 and d['conversationCount']==1525 and d['sourceLineCount']==3050 and d['utteranceCount']>=2600")
s=s.replace("assert d['recordingCount']==12440", "assert d['recordingCount']==10*d['utteranceCount']")
p.write_text(s,encoding='utf-8')

print('Patched VOICEVOX and Supertonic workflows for expanded conversation catalog')
