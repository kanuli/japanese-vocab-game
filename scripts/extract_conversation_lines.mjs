import fs from 'node:fs';
import vm from 'node:vm';

globalThis.window = globalThis;

const files = [
  'conversation-data-1.js',
  'conversation-data-2.js',
  'conversation-data-3.js',
  'conversation-data-4.js',
  'conversation-data-5.js',
  'conversation-expansion.js',
];

for (const file of files) {
  if (!fs.existsSync(file)) continue;
  vm.runInThisContext(fs.readFileSync(file, 'utf8'), { filename: file });
}

const scenes = globalThis.SITUATION_SCENES || [];
if (!Array.isArray(scenes) || !scenes.length) throw new Error('No conversation scenes loaded');

const seen = new Set();
const lines = [];
let total = 0;
for (const scene of scenes) {
  for (const item of scene.items || []) {
    for (const line of item.lines || []) {
      total++;
      const text = String(line.jp || '').trim();
      if (!text || seen.has(text)) continue;
      seen.add(text);
      lines.push(text);
    }
  }
}

fs.writeFileSync('conversation-lines.json', JSON.stringify({
  version: 1,
  sceneCount: scenes.length,
  totalLines: total,
  uniqueLines: lines.length,
  lines,
}, null, 2) + '\n');

console.log(`Extracted ${lines.length} unique Japanese lines from ${total} dialogue lines across ${scenes.length} scenes.`);
