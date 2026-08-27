#!/usr/bin/env node
'use strict';
const fs = require('fs');
const vm = require('vm');

const REPORT = 'data/inline_reading_cleanup_report.json';
const TARGETS = ['data/vocab_core_verified.js', 'data/advanced_vocab.js'];
const report = JSON.parse(fs.readFileSync(REPORT, 'utf8'));
const displayMap = report.displayMap || {};
const dirtyDisplays = new Set(Object.keys(displayMap));

function normalizeString(value) {
  if (Object.prototype.hasOwnProperty.call(displayMap, value)) return displayMap[value];
  const p = value.indexOf('|');
  if (p > 0) {
    const left = value.slice(0, p), right = value.slice(p + 1);
    if (Object.prototype.hasOwnProperty.call(displayMap, right)) return left + '|' + displayMap[right];
  }
  return value;
}

function lexicalParts(item) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) return null;
  const reading = String(item.reading ?? item.word ?? '').trim();
  const display = String(item.kanji ?? item.displayWord ?? item.display ?? item.written ?? item.word ?? reading).trim();
  if (!reading || !display) return null;
  return { reading, display, key: reading + '|' + display };
}

function hasDirtyDisplay(item) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) return false;
  const vals = [item.kanji, item.displayWord, item.display, item.written, item.word];
  return vals.some(v => typeof v === 'string' && dirtyDisplays.has(v));
}

function gradeRank(item) {
  const g = String(item?.grade ?? item?.teacherGrade ?? '').trim().toUpperCase();
  return ({ A: 4, B: 3, C: 2, D: 1 })[g] || 0;
}
function statusRank(item) {
  const s = String(item?.status ?? item?.teacherStatus ?? '').trim().toLowerCase();
  if (['manual','verified','teacher-verified'].includes(s)) return 5;
  if (s === 'direct') return 4;
  if (s.startsWith('direct')) return 3;
  if (['corroborated','validated'].includes(s)) return 2;
  return s ? 1 : 0;
}
function commonRank(item) {
  const v = item?.common ?? item?.teacherCommon;
  return [true,1,'1','true','yes','y'].includes(typeof v === 'string' ? v.toLowerCase() : v) ? 1 : 0;
}
function itemRank(item, wasDirty) {
  return [gradeRank(item), statusRank(item), commonRank(item), wasDirty ? 0 : 1,
    Object.values(item || {}).filter(v => v != null && v !== '').length];
}
function compareRank(a, b) {
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    const d = (a[i] || 0) - (b[i] || 0);
    if (d) return d;
  }
  return 0;
}

function mergeMissing(winner, loser) {
  const out = { ...winner };
  for (const [k, v] of Object.entries(loser || {})) {
    const cur = out[k];
    const curBlank = cur == null || cur === '' || (Array.isArray(cur) && cur.length === 0);
    const newUseful = v != null && v !== '' && (!Array.isArray(v) || v.length > 0);
    if (curBlank && newUseful) out[k] = v;
  }
  return out;
}

const stats = { dirtyObjects: 0, duplicatesRemoved: 0, lexicalArrays: 0 };

function normalizeArray(items) {
  const lexicalCount = items.reduce((n, x) => n + (lexicalParts(x) ? 1 : 0), 0);
  if (items.length && lexicalCount >= Math.max(1, Math.floor(items.length * 0.5))) {
    stats.lexicalArrays++;
    const out = [];
    const pos = new Map();
    for (const original of items) {
      const wasDirty = hasDirtyDisplay(original);
      if (wasDirty) stats.dirtyObjects++;
      const normalized = normalizeDeep(original);
      const parts = lexicalParts(normalized);
      if (!parts) { out.push(normalized); continue; }
      const rank = itemRank(original, wasDirty);
      if (!pos.has(parts.key)) {
        pos.set(parts.key, { index: out.length, rank });
        out.push(normalized);
        continue;
      }
      stats.duplicatesRemoved++;
      const prior = pos.get(parts.key);
      const priorItem = out[prior.index];
      if (compareRank(rank, prior.rank) > 0) {
        out[prior.index] = mergeMissing(normalized, priorItem);
        pos.set(parts.key, { index: prior.index, rank });
      } else {
        out[prior.index] = mergeMissing(priorItem, normalized);
      }
    }
    return out;
  }
  return items.map(normalizeDeep);
}

function normalizeDeep(value) {
  if (typeof value === 'string') return normalizeString(value);
  if (Array.isArray(value)) return normalizeArray(value);
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = normalizeDeep(v);
    return out;
  }
  return value;
}

function candidateNames(source) {
  const names = new Set();
  for (const re of [
    /(?:window|globalThis|self)\.([A-Za-z_$][\w$]*)\s*=/g,
    /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=/g,
  ]) {
    let m;
    while ((m = re.exec(source))) names.add(m[1]);
  }
  return [...names];
}

function loadExport(file) {
  const source = fs.readFileSync(file, 'utf8');
  const sandbox = { console: { log() {}, warn() {}, error() {} } };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: file, timeout: 30000 });
  const candidates = [];
  for (const name of candidateNames(source)) {
    let value;
    try { value = vm.runInContext(`typeof ${name} !== 'undefined' ? ${name} : undefined`, sandbox); }
    catch (_) { value = sandbox[name]; }
    if (value && (Array.isArray(value) || typeof value === 'object')) {
      let size = 0; try { size = JSON.stringify(value).length; } catch (_) {}
      candidates.push({ name, value, size });
    }
  }
  for (const [name, value] of Object.entries(sandbox)) {
    if (['window','self','console'].includes(name)) continue;
    if (!value || !(Array.isArray(value) || typeof value === 'object')) continue;
    if (candidates.some(x => x.name === name)) continue;
    let size = 0; try { size = JSON.stringify(value).length; } catch (_) {}
    candidates.push({ name, value, size });
  }
  candidates.sort((a, b) => b.size - a.size);
  if (!candidates.length) throw new Error(`${file}: no vocabulary object/array export found; names=${candidateNames(source).join(',')}`);
  return candidates[0];
}

function countLexical(value) {
  if (Array.isArray(value)) return value.reduce((n, x) => n + countLexical(x), 0);
  if (value && typeof value === 'object') {
    if (lexicalParts(value)) return 1;
    return Object.values(value).reduce((n, x) => n + countLexical(x), 0);
  }
  return 0;
}

const summaries = [];
for (const file of TARGETS) {
  if (!fs.existsSync(file)) continue;
  stats.dirtyObjects = 0; stats.duplicatesRemoved = 0; stats.lexicalArrays = 0;
  const exp = loadExport(file);
  const before = countLexical(exp.value);
  const normalized = normalizeDeep(exp.value);
  const after = countLexical(normalized);
  fs.writeFileSync(file, `window.${exp.name} = ${JSON.stringify(normalized, null, 2)};\n`, 'utf8');
  summaries.push({ file, global: exp.name, lexicalRowsBefore: before, lexicalRowsAfter: after,
    dirtyObjects: stats.dirtyObjects, duplicatesRemoved: stats.duplicatesRemoved, lexicalArrays: stats.lexicalArrays });
}
report.jsSources = summaries;
fs.writeFileSync(REPORT, JSON.stringify(report, null, 2) + '\n', 'utf8');
console.log(JSON.stringify(summaries, null, 2));
