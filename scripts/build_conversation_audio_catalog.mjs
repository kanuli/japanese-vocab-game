import fs from 'node:fs';
import vm from 'node:vm';

const files = [1,2,3,4,5].map(n => `conversation-data-${n}.js`);
global.window = {};
for (const file of files) {
  const src = fs.readFileSync(file, 'utf8');
  vm.runInThisContext(src, { filename: file });
}

const scenes = global.window.SITUATION_SCENES || [];
if (!Array.isArray(scenes) || !scenes.length) throw new Error('No conversation scenes loaded');

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
const byNorm = new Map();
const lines = {};
const textMap = {};
for (const scene of scenes) {
  for (const item of scene.items || []) {
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
  version: 1,
  status: 'catalog',
  engine: 'supertonic-3',
  language: 'ja',
  sourceLineCount,
  utteranceCount: Object.keys(lines).length,
  voiceCount: Object.keys(voices).length,
  voices,
  lines,
  textMap
};

if (sourceLineCount !== 260) throw new Error(`Expected 260 source lines, got ${sourceLineCount}`);
if (out.utteranceCount < 200 || out.utteranceCount > 260) throw new Error(`Unexpected unique utterance count ${out.utteranceCount}`);
if (out.voiceCount !== 10) throw new Error('Expected 10 Supertonic voices');
fs.writeFileSync('conversation-audio-catalog.json', JSON.stringify(out, null, 2) + '\n');
console.log(`Conversation audio catalog: ${sourceLineCount} source lines -> ${out.utteranceCount} unique utterances × ${out.voiceCount} voices`);
