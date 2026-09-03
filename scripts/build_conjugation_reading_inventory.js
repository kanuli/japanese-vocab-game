#!/usr/bin/env node
'use strict';
/**
 * Frozen conjugation reading inventory.
 * Workers MUST consume the written JSON; they must not rebuild this list.
 * Uses the same runtime WordlistConjugation classifier as the wordlist page.
 */
var fs = require('fs');
var path = require('path');
var crypto = require('crypto');
var conj = require(path.resolve(__dirname, '..', 'wordlist-conjugation.js'));

var ROOT = path.resolve(__dirname, '..');
var INVENTORY_VERSION = process.env.INVENTORY_VERSION || 'v1';
var CHUNK_SIZE = Math.max(1, parseInt(process.env.CHUNK_SIZE || '400', 10));
var PUBLIC_BUNDLE_COUNT = Math.max(1, parseInt(process.env.PUBLIC_BUNDLE_COUNT || '20', 10));
var ID_PREFIX = process.env.ID_PREFIX || 'conj-inv-v1';
var WORDS_PATH = process.env.CONJ_WORDS_JSON || path.join(ROOT, 'word-supertonic3-conj-words.json');
var OUT = process.env.OUT || path.join(ROOT, 'word-conjugation-reading-inventory-' + INVENTORY_VERSION + '.json');
var SMOKE_OUT = process.env.SMOKE_OUT || path.join(ROOT, 'word-conjugation-reading-inventory-smoke-' + INVENTORY_VERSION + '.json');
var SMOKE_COUNT = Math.max(0, parseInt(process.env.SMOKE_COUNT || '40', 10));
var LEGACY_CATALOG = process.env.LEGACY_F3_CATALOG || '';
var SKIP_EXISTING = process.env.SKIP_EXISTING === '1';

function sha256(s) {
  return crypto.createHash('sha256').update(s).digest('hex');
}
function readingId(reading) {
  return sha256(ID_PREFIX + '\0' + reading).slice(0, 16);
}

function loadWords(p) {
  var raw = fs.readFileSync(p, 'utf8');
  var data = JSON.parse(raw);
  return Array.isArray(data) ? data : (data.words || []);
}

function enumerate(words) {
  var unique = Object.create(null);
  var verbs = 0, forms = 0, skipped = 0, duplicates = 0;
  for (var i = 0; i < words.length; i++) {
    var w = words[i];
    if (!conj.canConjugate(w)) { skipped++; continue; }
    verbs++;
    var result = conj.conjugate(w);
    var rows = (result.forms || []).concat(result.extended || []);
    for (var j = 0; j < rows.length; j++) {
      var row = rows[j];
      if (!row || !row.reading) continue;
      forms++;
      var r = conj.normalizeReading(row.reading);
      if (!r) continue;
      if (unique[r]) { duplicates++; unique[r].count++; continue; }
      unique[r] = { reading: r, written: row.written || r, count: 1 };
      if (row.written) unique[r].written = unique[r].written || row.written;
    }
  }
  var items = Object.keys(unique).sort().map(function (k) { return unique[k]; });
  return { verbs: verbs, forms: forms, skipped: skipped, duplicates: duplicates, items: items };
}

function legacyReadings(catalogPath) {
  if (!catalogPath || !fs.existsSync(catalogPath)) return Object.create(null);
  var d = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
  var words = d.words || {};
  var out = Object.create(null);
  Object.keys(words).forEach(function (k) {
    var r = conj.normalizeReading(String(k).split('|')[0]);
    if (r) out[r] = { key: k, id: words[k][0], shard: words[k][1] };
  });
  return out;
}

function build() {
  if (SKIP_EXISTING && fs.existsSync(OUT)) {
    var existing = JSON.parse(fs.readFileSync(OUT, 'utf8'));
    console.error('Reusing existing inventory', OUT, 'unique', existing.uniqueReadingCount);
    return existing;
  }
  var words = loadWords(WORDS_PATH);
  var vocabSourceHash = sha256(fs.readFileSync(WORDS_PATH));
  var enumed = enumerate(words);
  var ids = Object.create(null);
  var readings = [];
  for (var i = 0; i < enumed.items.length; i++) {
    var row = enumed.items[i];
    var id = readingId(row.reading);
    if (ids[id]) throw new Error('Reading ID collision ' + id);
    ids[id] = true;
    readings.push([id, row.reading, row.written]);
  }
  var chunkCount = readings.length ? Math.ceil(readings.length / CHUNK_SIZE) : 0;
  var publicBundleSize = readings.length ? Math.ceil(readings.length / PUBLIC_BUNDLE_COUNT) : 0;
  var canonical = readings.map(function (x) { return x[0] + '\t' + x[1]; }).join('\n');
  var freezeHash = sha256(INVENTORY_VERSION + '\n' + CHUNK_SIZE + '\n' + canonical);
  var payload = {
    inventoryVersion: INVENTORY_VERSION,
    idPrefix: ID_PREFIX,
    vocabSource: path.basename(WORDS_PATH),
    vocabSourceHash: vocabSourceHash,
    classifier: 'wordlist-conjugation.js',
    verbCount: enumed.verbs,
    formInstanceCount: enumed.forms,
    uniqueReadingCount: readings.length,
    duplicateCount: enumed.duplicates,
    skippedCount: enumed.skipped,
    chunkSize: CHUNK_SIZE,
    chunkCount: chunkCount,
    publicBundleCount: PUBLIC_BUNDLE_COUNT,
    publicBundleSize: publicBundleSize,
    freezeHash: freezeHash,
    note: 'Generation chunks are not public runtime shards. Compact later into ~' + PUBLIC_BUNDLE_COUNT + ' range-readable public bundles. Workers must consume this file and must not rebuild inventory.',
    readings: readings
  };
  fs.writeFileSync(OUT, JSON.stringify(payload));
  console.error('Wrote', OUT, 'unique', readings.length, 'chunks', chunkCount, 'chunkSize', CHUNK_SIZE, 'publicBundles', PUBLIC_BUNDLE_COUNT, 'freeze', freezeHash.slice(0, 12));

  var legacy = legacyReadings(LEGACY_CATALOG);
  var legacyCount = Object.keys(legacy).length;
  var smoke = [];
  if (SMOKE_COUNT > 0) {
    for (var s = 0; s < readings.length && smoke.length < SMOKE_COUNT; s++) {
      if (legacy[readings[s][1]]) continue;
      smoke.push(readings[s]);
    }
    var smokeCanonical = smoke.map(function (x) { return x[0] + '\t' + x[1]; }).join('\n');
    var smokePayload = {
      inventoryVersion: 'smoke-' + INVENTORY_VERSION,
      parentInventoryVersion: INVENTORY_VERSION,
      parentFreezeHash: freezeHash,
      idPrefix: ID_PREFIX,
      vocabSourceHash: vocabSourceHash,
      classifier: 'wordlist-conjugation.js',
      verbCount: enumed.verbs,
      formInstanceCount: enumed.forms,
      uniqueReadingCount: smoke.length,
      duplicateCount: 0,
      skippedCount: 0,
      chunkSize: smoke.length || 1,
      chunkCount: smoke.length ? 1 : 0,
      publicBundleCount: PUBLIC_BUNDLE_COUNT,
      publicBundleSize: publicBundleSize,
      freezeHash: sha256('smoke-' + INVENTORY_VERSION + '\n' + smokeCanonical),
      smoke: true,
      note: 'Tiny smoke slice of readings not present in published F3 v1. Do not treat as 100% coverage.',
      readings: smoke
    };
    fs.writeFileSync(SMOKE_OUT, JSON.stringify(smokePayload));
    console.error('Wrote smoke', SMOKE_OUT, 'readings', smoke.length, 'legacySkipped', legacyCount);
  }
  return payload;
}

if (require.main === module) build();
module.exports = { build: build, readingId: readingId, enumerate: enumerate, sha256: sha256 };
