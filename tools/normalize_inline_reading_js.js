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

function normalizeDeep(value) {
  if (typeof value === 'string') return normalizeString(value);
  if (Array.isArray(value)) return value.map(normalizeDeep);
  if (value && typeof value === 'object') {
    const out = {};
    for (const [k, v] of Object.entries(value)) out[k] = normalizeDeep(v);
    return out;
  }
  return value;
}

function lexicalParts(item) {
  if (!item || typeof item !== 'object') return null;
  const reading = String(item.reading ?? item.word ?? '').trim();
  const display = String(item.kanji ?? item.displayWord ?? item.display ?? item.written ?? item.word ?? reading).trim();
  if (!reading || !display) return null;
  return { reading, display, key: reading + '|' + display };
}

function hasDirtyDisplay(item) {
  if (!item || typeof item !== 'object') return false;
  const vals = [item.kanji, item.displayWord, item.display, item.written, item.word];
  return vals.some(v => typeof v === 'string' && dirtyDisplays.has(v));
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

function normalizeAndDedupeArray(items) {
  const out = [];
  const pos = new Map();
  let dirtyObjects = 0, duplicatesRemoved = 0;
  for (const original of items) {
    const wasDirty = hasDirtyDisplay(original);
    if (wasDirty) dirtyObjects++;
    const normalized = normalizeDeep(original);
    const parts = lexicalParts(normalized);
    if (!parts) {
      out.push(normalized);
      continue;
    }
    if (!pos.has(parts.key)) {
      pos.set(parts.key, { index: out.length, wasDirty });
      out.push(normalized);
      continue;
    }
    duplicatesRemoved++;
    const prior = pos.get(parts.key);
    const priorItem = out[prior.index];
    // Prefer the originally clean object; otherwise preserve the first row. Fill only blank fields.
    if (prior.wasDirty && !wasDirty) {
      out[prior.index] = mergeMissing(normalized, priorItem);
      pos.set(parts.key, { index: prior.index, wasDirty: false });
    } else {
      out[prior.index] = mergeMissing(priorItem, normalized);
    }
  }
  return { items: out, dirtyObjects, duplicatesRemoved };
}

function loadGlobals(file) {
  const source = fs.readFileSync(file, 'utf8');
  const sandbox = { console: { log() {}, warn() {}, error() {} } };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: file, timeout: 30000 });
  const arrays = Object.entries(sandbox)
    .filter(([k, v]) => !['window','self','console'].includes(k) && Array.isArray(v))
    .sort((a, b) => b[1].length - a[1].length);
  if (!arrays.length) throw new Error(`${file}: no global vocabulary array found`);
  return arrays;
}

const summaries = [];
for (const file of TARGETS) {
  if (!fs.existsSync(file)) continue;
  const arrays = loadGlobals(file);
  if (arrays.length !== 1) {
    throw new Error(`${file}: expected exactly one global array, found ${arrays.map(x => x[0]).join(', ')}`);
  }
  const [name, items] = arrays[0];
  const result = normalizeAndDedupeArray(items);
  fs.writeFileSync(file, `window.${name} = ${JSON.stringify(result.items, null, 2)};\n`, 'utf8');
  summaries.push({ file, global: name, rowsBefore: items.length, rowsAfter: result.items.length,
    dirtyObjects: result.dirtyObjects, duplicatesRemoved: result.duplicatesRemoved });
}

report.jsSources = summaries;
fs.writeFileSync(REPORT, JSON.stringify(report, null, 2) + '\n', 'utf8');
console.log(JSON.stringify(summaries, null, 2));
