import fs from 'node:fs';
import vm from 'node:vm';

const files = [1,2,3,4,5].map(n => `conversation-data-${n}.js`);
global.window = {};
for (const file of files) {
  const src = fs.readFileSync(file, 'utf8');
  vm.runInThisContext(src, { filename: file });
}
// The expansion layer adds 20 more conversations to each of the 26 scenes.
const expansion = fs.readFileSync('conversation-expansion.js', 'utf8');
vm.runInThisContext(expansion, { filename: 'conversation-expansion.js' });

const scenes = global.window.SITUATION_SCENES || [];
if (!Array.isArray(scenes) || scenes.length !== 26) throw new Error(`Expected 26 conversation scenes, got ${scenes.length}`);

const voices = {
  F1: '🌙 沉穩低柔女聲（F1）',
  F2: '🌸 明亮活潑女聲（F2）',
  F3: '🎙️ 專業播音女聲（F3）',
  F4: '✨ 清晰自信女聲（F4）',
  F5: '💕 溫柔療癒女聲（F5）',
  M1: '⚡ 活力自信男聲（M1）',
  M2: '🌑 低沉穩重男聲（M2）',
  M3: '🧭 權威專業男聲（M3）',
  M4: '🙂 柔和親切男聲（M4）',
  M5: '📖 溫暖舒緩男聲（M5）'
};

function norm(s) {
  return String(s || '').normalize('NFKC').replace(/[\s　。、，,.！？!?「」『』（）()]/g, '').trim();
}

let sourceLineCount = 0;
let conversationCount = 0;
const levelCounts = {N1:0,N2:0,N3:0,N4:0,N5:0};
const byNorm = new Map();
const lines = {};
const textMap = {};
for (const scene of scenes) {
  if ((scene.items || []).length !== 25) throw new Error(`${scene.id}: expected 25 conversations, got ${(scene.items||[]).length}`);
  for (const item of scene.items || []) {
    conversationCount++;
    levelCounts[item.level] = (levelCounts[item.level] || 0) + 1;
    for (const line of item.lines || []) {
      sourceLineCount++;
      const text = String(line.jp || '').trim();
      const key = norm(text);
      if (!text || !key) continue;
      let id = byNorm.get(key);
      if (!id) {
        id = `u${String(byNorm.size + 1).padStart(4, '0')}`;
        byNorm.set(key, id);
        lines[id] = { text, norm: key };
      }
      textMap[key] = id;
    }
  }
}

const out = {
  version: 2,
  status: 'catalog',
  engine: 'shared-conversation-audio',
  language: 'ja',
  sceneCount: scenes.length,
  conversationCount,
  sourceLineCount,
  utteranceCount: Object.keys(lines).length,
  voiceCount: Object.keys(voices).length,
  levelCounts,
  voices,
  lines,
  textMap
};

if (conversationCount !== 650) throw new Error(`Expected 650 conversations, got ${conversationCount}`);
if (sourceLineCount !== 1300) throw new Error(`Expected 1300 source lines, got ${sourceLineCount}`);
if (out.utteranceCount !== 1244) throw new Error(`Expected 1244 unique utterances, got ${out.utteranceCount}`);
for (const lv of ['N1','N2','N3','N4','N5']) if (levelCounts[lv] !== 130) throw new Error(`${lv}: expected 130 conversations, got ${levelCounts[lv]}`);
if (out.voiceCount !== 10) throw new Error('Expected 10 Supertonic voices');
fs.writeFileSync('conversation-audio-catalog.json', JSON.stringify(out, null, 2) + '\n');
console.log(`Conversation audio catalog: ${conversationCount} conversations / ${sourceLineCount} source lines -> ${out.utteranceCount} unique utterances × ${out.voiceCount} Supertonic voices`);
